"""Arm payload builder emits exactly the D2-frozen field sets; fixed policy runs one request."""

import json

import pytest

from speech_aware_evidence_acquisition.core import policies  # noqa: F401 (registration)
from speech_aware_evidence_acquisition.core.base import (
    POLICIES,
    EvidenceItem,
    SampleContext,
)
from speech_aware_evidence_acquisition.core.policies import ArmError, build_arm_payload
from speech_aware_evidence_acquisition.core.tracing import TraceSink
from speech_aware_evidence_acquisition.data.loader import SampleRef
from speech_aware_evidence_acquisition.e0.d2_leakage import ARM_VISIBLE_FIELDS

_REF = SampleRef(
    carrier_lock_key="earnings21-original",
    sample_id="4000001",
    media_relpath="datasets/earnings21-22/earnings21/media/4000001.mp3",
    audio_seconds=100.5,
    sample_rate_hz=16000,
)
_EVIDENCE = [
    EvidenceItem(
        evidence_id="conec/4000001",
        source_uri="conec://earnings21/contexts/4000001.txt",
        content="ctx",
        provenance={
            "lock_key": "conec",
            "relpath": "earnings21/contexts/4000001.txt",
            "sha256": "0" * 64,
        },
    )
]
_DECODING = {"temperature": 0, "seed": 20260803}


def test_bare_core_exact_fields():
    payload = build_arm_payload("bare-core", _REF, "req-1", "Transcribe.", _DECODING)
    assert set(payload) == set(ARM_VISIBLE_FIELDS["bare-core"])
    assert payload["history"] == []
    assert payload["speech_ref"] == "earnings21-original/4000001"


def test_bare_core_refuses_evidence():
    with pytest.raises(ArmError, match="bare-core"):
        build_arm_payload("bare-core", _REF, "req-1", "T.", _DECODING, evidence=_EVIDENCE)


def test_fixed_legal_context_carries_evidence_and_provenance():
    payload = build_arm_payload(
        "fixed-legal-context", _REF, "req-1", "T.", _DECODING, evidence=_EVIDENCE
    )
    assert set(payload) == set(ARM_VISIBLE_FIELDS["fixed-legal-context"])
    assert payload["supplied_evidence"] == [_EVIDENCE[0].runtime_view()]
    assert payload["evidence_provenance"] == [_EVIDENCE[0].provenance_view()]


def test_fixed_legal_context_requires_evidence():
    with pytest.raises(ArmError, match="evidence"):
        build_arm_payload("fixed-legal-context", _REF, "req-1", "T.", _DECODING)


def test_fixed_retrieval_requires_query_and_evidence():
    payload = build_arm_payload(
        "fixed-retrieval", _REF, "req-1", "T.", _DECODING,
        evidence=_EVIDENCE, retrieval_query="acme q2",
    )
    assert set(payload) == set(ARM_VISIBLE_FIELDS["fixed-retrieval"])
    assert payload["retrieval_query"] == "acme q2"
    with pytest.raises(ArmError, match="retrieval_query"):
        build_arm_payload(
            "fixed-retrieval", _REF, "req-1", "T.", _DECODING, evidence=_EVIDENCE
        )


def test_unknown_arm_refused():
    with pytest.raises(ArmError, match="unknown arm"):
        build_arm_payload("oracle-arm", _REF, "req-1", "T.", _DECODING)


# ---------------------------------------------------------------------------
# Acoustic exemplar bank (core.exemplars, M-C-prime prep infrastructure):
# no D2-frozen arm declares "exemplar_bank" yet, so the default (None) is a
# byte-identical no-op and every arm registered today fails closed when one
# is supplied -- exercised here by temporarily extending "bare-core"'s own
# ARM_VISIBLE_FIELDS entry (monkeypatch, reverted at teardown) rather than
# registering a real new arm, which would need its own D2 receipt.
# ---------------------------------------------------------------------------

_EXEMPLAR_BANK = [
    {"media_relpath": "derived/exemplar-pairs/mc2-v1/4000001/alpha.wav", "label": "alpha"}
]


def test_build_arm_payload_omitting_exemplar_bank_is_byte_identical():
    without = build_arm_payload("bare-core", _REF, "req-1", "T.", _DECODING)
    with_explicit_none = build_arm_payload(
        "bare-core", _REF, "req-1", "T.", _DECODING, exemplar_bank=None
    )
    assert without == with_explicit_none
    assert "exemplar_bank" not in without


@pytest.mark.parametrize(
    "arm,kwargs",
    [
        ("bare-core", {}),
        ("fixed-legal-context", {"evidence": _EVIDENCE}),
        ("fixed-retrieval", {"evidence": _EVIDENCE, "retrieval_query": "acme q2"}),
    ],
)
def test_build_arm_payload_refuses_exemplar_bank_for_every_arm_registered_today(arm, kwargs):
    with pytest.raises(ArmError, match="exemplar_bank"):
        build_arm_payload(arm, _REF, "req-1", "T.", _DECODING, exemplar_bank=[], **kwargs)


def test_build_arm_payload_refuses_a_nonempty_exemplar_bank_too():
    with pytest.raises(ArmError, match="exemplar_bank"):
        build_arm_payload(
            "bare-core", _REF, "req-1", "T.", _DECODING, exemplar_bank=_EXEMPLAR_BANK
        )


def test_build_arm_payload_attaches_exemplar_bank_for_an_arm_that_declares_it(monkeypatch):
    monkeypatch.setitem(
        ARM_VISIBLE_FIELDS, "bare-core", ARM_VISIBLE_FIELDS["bare-core"] + ("exemplar_bank",)
    )
    payload = build_arm_payload(
        "bare-core", _REF, "req-1", "T.", _DECODING, exemplar_bank=_EXEMPLAR_BANK
    )
    assert set(payload) == set(ARM_VISIBLE_FIELDS["bare-core"])
    assert payload["exemplar_bank"] == _EXEMPLAR_BANK


def test_build_arm_payload_attaches_an_empty_exemplar_bank_for_an_arm_that_declares_it(
    monkeypatch,
):
    """An empty bank is a legal v3 shape (core.model.transport's own module
    docstring: an empty bank reduces to v2's shape) -- attached, never
    dropped, once the arm declares the field."""

    monkeypatch.setitem(
        ARM_VISIBLE_FIELDS, "bare-core", ARM_VISIBLE_FIELDS["bare-core"] + ("exemplar_bank",)
    )
    payload = build_arm_payload("bare-core", _REF, "req-1", "T.", _DECODING, exemplar_bank=[])
    assert payload["exemplar_bank"] == []


# ---------------------------------------------------------------------------
# New arms (2026-08-13): "exemplar-context" (M-C-prime static acoustic-supply
# arm, fixed-legal-context's own field set + "exemplar_bank") and
# "fixed-legal-context-replay" (the obs-replay-loop REPLAY-scoped arm,
# fixed-legal-context's own field set + "exemplar_bank" + "delta_candidates")
# -- registered rather than mutating a frozen entry (core.policies module
# docstring: "the arm payload vocabulary never grows without a new D2
# receipt"). Real, D2-registered arms: no ARM_VISIBLE_FIELDS monkeypatch.
# ---------------------------------------------------------------------------


def test_exemplar_context_is_fixed_legal_context_plus_exemplar_bank():
    assert set(ARM_VISIBLE_FIELDS["exemplar-context"]) == set(
        ARM_VISIBLE_FIELDS["fixed-legal-context"]
    ) | {"exemplar_bank"}


def test_fixed_legal_context_replay_is_fixed_legal_context_plus_both_tiers():
    assert set(ARM_VISIBLE_FIELDS["fixed-legal-context-replay"]) == set(
        ARM_VISIBLE_FIELDS["fixed-legal-context"]
    ) | {"exemplar_bank", "delta_candidates"}


def test_exemplar_context_attaches_evidence_and_exemplar_bank_end_to_end():
    payload = build_arm_payload(
        "exemplar-context",
        _REF,
        "req-1",
        "T.",
        _DECODING,
        evidence=_EVIDENCE,
        exemplar_bank=_EXEMPLAR_BANK,
    )
    assert set(payload) == set(ARM_VISIBLE_FIELDS["exemplar-context"])
    assert payload["supplied_evidence"] == [_EVIDENCE[0].runtime_view()]
    assert payload["exemplar_bank"] == _EXEMPLAR_BANK


def test_exemplar_context_requires_evidence_like_its_base_arm():
    with pytest.raises(ArmError, match="evidence"):
        build_arm_payload(
            "exemplar-context", _REF, "req-1", "T.", _DECODING, exemplar_bank=_EXEMPLAR_BANK
        )


def test_exemplar_context_refuses_a_retrieval_query_like_its_base_arm():
    with pytest.raises(ArmError, match="retrieval query"):
        build_arm_payload(
            "exemplar-context",
            _REF,
            "req-1",
            "T.",
            _DECODING,
            evidence=_EVIDENCE,
            retrieval_query="acme q2",
            exemplar_bank=_EXEMPLAR_BANK,
        )


def test_fixed_legal_context_replay_attaches_evidence_bank_and_candidates_end_to_end():
    delta = [{"text": "acme"}]
    payload = build_arm_payload(
        "fixed-legal-context-replay",
        _REF,
        "req-1",
        "T.",
        _DECODING,
        evidence=_EVIDENCE,
        exemplar_bank=_EXEMPLAR_BANK,
        delta_candidates=delta,
    )
    assert set(payload) == set(ARM_VISIBLE_FIELDS["fixed-legal-context-replay"])
    assert payload["supplied_evidence"] == [_EVIDENCE[0].runtime_view()]
    assert payload["exemplar_bank"] == _EXEMPLAR_BANK
    assert payload["delta_candidates"] == delta


def test_fixed_legal_context_replay_accepts_empty_tiers_too():
    """An empty bank/candidate list is legal (v3 shape); once an arm
    declares the field it must be present, but it may be empty."""

    payload = build_arm_payload(
        "fixed-legal-context-replay",
        _REF,
        "req-1",
        "T.",
        _DECODING,
        evidence=_EVIDENCE,
        exemplar_bank=[],
        delta_candidates=[],
    )
    assert payload["exemplar_bank"] == []
    assert payload["delta_candidates"] == []


@pytest.mark.parametrize(
    "arm,kwargs",
    [
        ("bare-core", {}),
        ("fixed-retrieval", {"evidence": _EVIDENCE, "retrieval_query": "acme q2"}),
    ],
)
def test_arms_that_still_do_not_declare_exemplar_bank_stay_fail_closed(arm, kwargs):
    """Fail-closed matrix: registering "exemplar-context"/
    "fixed-legal-context-replay" changes nothing for the arms that do NOT
    declare "exemplar_bank" -- they refuse it exactly as before."""

    with pytest.raises(ArmError, match="exemplar_bank"):
        build_arm_payload(arm, _REF, "req-1", "T.", _DECODING, exemplar_bank=[], **kwargs)


def test_fixed_legal_context_itself_still_refuses_exemplar_bank():
    """"exemplar-context" is a SIBLING arm, not a mutation of
    "fixed-legal-context" -- the base arm's own frozen field set is
    untouched and still fails closed on an exemplar bank."""

    with pytest.raises(ArmError, match="exemplar_bank"):
        build_arm_payload(
            "fixed-legal-context", _REF, "req-1", "T.", _DECODING,
            evidence=_EVIDENCE, exemplar_bank=[],
        )


def test_exemplar_context_omitting_the_bank_fails_closed():
    """Once an arm declares "exemplar_bank", the field is REQUIRED -- an
    omitted (None) bank leaves the payload's key set short of the D2 freeze."""

    with pytest.raises(ArmError, match="diverges from the D2 freeze"):
        build_arm_payload(
            "exemplar-context", _REF, "req-1", "T.", _DECODING, evidence=_EVIDENCE
        )


def test_fixed_legal_context_replay_omitting_delta_candidates_fails_closed():
    with pytest.raises(ArmError, match="diverges from the D2 freeze"):
        build_arm_payload(
            "fixed-legal-context-replay", _REF, "req-1", "T.", _DECODING,
            evidence=_EVIDENCE, exemplar_bank=[],
        )


class _CapturingTransport:
    """Fake transport asserting the exact payload the adapter forwards --
    "mock transport asserting tier contents" for a new, real D2-registered
    arm (as opposed to test_policies.py's other tests above, which stop at
    build_arm_payload and never reach the adapter's own allowlist gate)."""

    def __init__(self, text: str = "hello world") -> None:
        self.captured: list[dict] = []
        self._text = text

    def __call__(self, request_bytes: bytes) -> bytes:
        self.captured.append(json.loads(request_bytes.decode("utf-8")))
        return json.dumps({"text": self._text, "usage": {}}).encode()


def test_fixed_policy_threads_exemplar_bank_end_to_end_for_the_new_arm(tmp_path):
    """New-arm resolution + payload attachment, end to end: core.policies.
    FixedPolicy -> build_arm_payload -> core.model.FrozenCoreAdapter's own
    allowlist gate -> the transport actually receives the exemplar bank on
    the wire payload for "exemplar-context" -- the arm this policy could
    not previously carry an exemplar bank for at all (core.policies module
    comment: FixedPolicy never threaded SampleContext.exemplar_bank)."""

    from speech_aware_evidence_acquisition.contracts import ExecutionPlan
    from speech_aware_evidence_acquisition.core.base import PayloadBindingContext
    from speech_aware_evidence_acquisition.core.model import FrozenCoreAdapter

    sink = TraceSink(tmp_path / "run", "SAEA-E-000-policy")
    plan = ExecutionPlan(
        run_id="SAEA-E-000-policy",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="earnings21-original",
        split_role="discovery",
        split_identity_hash="a" * 64,
        planned_model_calls=5,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1000,
        protocol_hash="b" * 64,
        attempt_id="attempt-0001",
    )
    data_root = tmp_path / "data"
    media = data_root / _REF.media_relpath
    media.parent.mkdir(parents=True, exist_ok=True)
    media.write_bytes(b"fake-mp3-bytes")
    binding = PayloadBindingContext(
        carrier_lock_key=_REF.carrier_lock_key,
        allowed_sample_ids=frozenset({_REF.sample_id}),
        sample_facts={_REF.sample_id: (_REF.audio_seconds, _REF.sample_rate_hz)},
        data_root=data_root,
        carrier_root=data_root / "datasets" / "earnings21-22" / "earnings21",
    )
    transport = _CapturingTransport()
    adapter = FrozenCoreAdapter(
        gate=_OpenGate(),
        plan=plan,
        arm="exemplar-context",
        transport=transport,
        sink=sink,
        binding=binding,
    )
    ctx = SampleContext(
        sample=_REF, evidence=_EVIDENCE, adapter=adapter, sink=sink, arm="exemplar-context",
        task_instruction="T.", decoding_params=_DECODING, request_id_base="req-0001",
        exemplar_bank=_EXEMPLAR_BANK,
    )
    outcome = POLICIES.resolve("fixed").run_sample(ctx)

    assert outcome.admitted is True
    assert len(transport.captured) == 1
    wire_payload = transport.captured[0]
    assert wire_payload["exemplar_bank"] == _EXEMPLAR_BANK
    assert wire_payload["supplied_evidence"] == [_EVIDENCE[0].runtime_view()]


def test_fixed_policy_stays_byte_identical_for_arms_without_an_exemplar_bank(tmp_path):
    """Byte-identity guard: threading ctx.exemplar_bank through FixedPolicy
    changes nothing for a run that never resolved a manifest at all
    (ctx.exemplar_bank stays None -- build_arm_payload's own "default None
    omits the field" no-op)."""

    from speech_aware_evidence_acquisition.contracts import ExecutionPlan
    from speech_aware_evidence_acquisition.core.base import PayloadBindingContext
    from speech_aware_evidence_acquisition.core.model import FrozenCoreAdapter

    sink = TraceSink(tmp_path / "run", "SAEA-E-000-policy")
    plan = ExecutionPlan(
        run_id="SAEA-E-000-policy",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="earnings21-original",
        split_role="discovery",
        split_identity_hash="a" * 64,
        planned_model_calls=5,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1000,
        protocol_hash="b" * 64,
        attempt_id="attempt-0001",
    )
    data_root = tmp_path / "data"
    media = data_root / _REF.media_relpath
    media.parent.mkdir(parents=True, exist_ok=True)
    media.write_bytes(b"fake-mp3-bytes")
    binding = PayloadBindingContext(
        carrier_lock_key=_REF.carrier_lock_key,
        allowed_sample_ids=frozenset({_REF.sample_id}),
        sample_facts={_REF.sample_id: (_REF.audio_seconds, _REF.sample_rate_hz)},
        data_root=data_root,
        carrier_root=data_root / "datasets" / "earnings21-22" / "earnings21",
    )
    transport = _CapturingTransport()
    adapter = FrozenCoreAdapter(
        gate=_OpenGate(), plan=plan, arm="bare-core", transport=transport, sink=sink,
        binding=binding,
    )
    ctx = SampleContext(
        sample=_REF, evidence=[], adapter=adapter, sink=sink, arm="bare-core",
        task_instruction="T.", decoding_params=_DECODING, request_id_base="req-0001",
    )
    POLICIES.resolve("fixed").run_sample(ctx)
    assert "exemplar_bank" not in transport.captured[0]


class _OpenGate:
    def assert_model_touch_allowed(self, plan):
        pass


def test_fixed_policy_runs_one_request_and_admits(tmp_path):
    from speech_aware_evidence_acquisition.contracts import ExecutionPlan
    from speech_aware_evidence_acquisition.core.base import PayloadBindingContext
    from speech_aware_evidence_acquisition.core.model import FrozenCoreAdapter

    sink = TraceSink(tmp_path / "run", "SAEA-E-000-policy")
    plan = ExecutionPlan(
        run_id="SAEA-E-000-policy",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="earnings21-original",
        split_role="discovery",
        split_identity_hash="a" * 64,
        planned_model_calls=5,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1000,
        protocol_hash="b" * 64,
        attempt_id="attempt-0001",
    )
    data_root = tmp_path / "data"
    media = data_root / _REF.media_relpath
    media.parent.mkdir(parents=True, exist_ok=True)
    media.write_bytes(b"fake-mp3-bytes")
    binding = PayloadBindingContext(
        carrier_lock_key=_REF.carrier_lock_key,
        allowed_sample_ids=frozenset({_REF.sample_id}),
        sample_facts={_REF.sample_id: (_REF.audio_seconds, _REF.sample_rate_hz)},
        data_root=data_root,
        carrier_root=data_root / "datasets" / "earnings21-22" / "earnings21",
    )
    adapter = FrozenCoreAdapter(
        gate=_OpenGate(),
        plan=plan,
        arm="bare-core",
        transport=lambda b: json.dumps({"text": "hi", "usage": {}}).encode(),
        sink=sink,
        binding=binding,
    )
    ctx = SampleContext(
        sample=_REF, evidence=[], adapter=adapter, sink=sink, arm="bare-core",
        task_instruction="T.", decoding_params=_DECODING, request_id_base="req-0001",
    )
    outcome = POLICIES.resolve("fixed").run_sample(ctx)
    assert outcome.sample_id == "4000001"
    assert outcome.admitted is True
    assert outcome.request_ids == ("req-0001",)
    assert "req-0001/use" in sink.manifest()
