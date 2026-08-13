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
