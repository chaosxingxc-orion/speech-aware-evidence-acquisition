"""obs-agent-loop-ojw: the openJiuwen executor against the plain reference.

Red line 3 of the adoption memo (docs/readiness/2026-08-08-openjiuwen-
adoption.md): the openJiuwen executor must reproduce the plain-Python
``obs-agent-loop`` policy's behaviour on the same inputs before any
registered run uses it. Both executors run here over the SAME synthetic
fixtures (scripted fake adapter, synthetic PCM, monkeypatched decode — the
exact ``_World`` harness of ``test_obs_loop_policy``) and must produce:

- identical accepted-span sequences (re-derived per side from that side's
  own OBS trace records through the frozen pure functions, and pinned a
  second way by the tail-conditioning scenario, whose 4000-char tail embeds
  the entire stitched-so-far text into every subsequent request payload);
- identical slice derivation records (byte-for-byte);
- identical stitched output text and outputs-row hashes;
- identical trace record sequences (only the fake adapter emits no
  MODEL_REQUEST/COST records on either side; the volatile
  ``latency_seconds`` field is stripped defensively).

Determinism: the framework body is a LINEAR four-node chain, so every
Pregel super-step has exactly one ready node; ``test_determinism_five_runs``
verifies empirically that five fresh executor runs produce byte-identical
artifacts (and match the plain reference).

Requires openjiuwen (skip marker otherwise — D2 gate: the suite must pass
with openjiuwen absent; see ``test_obs_loop_ojw_absent.py``).
"""

import dataclasses
import hashlib
import json

import pytest

pytest.importorskip(
    "openjiuwen",
    reason="openjiuwen not installed; the ojw executor is exercised only in "
    "the pinned WSL research venv (D2: never a pyproject dependency)",
)

import speech_aware_evidence_acquisition.core  # noqa: F401,E402 (populate registries)
from speech_aware_evidence_acquisition.core.base import POLICIES, EvidenceItem  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.obs_audio import (  # noqa: E402
    accept_up_to_boundary,
    parse_boundary_response,
)
from speech_aware_evidence_acquisition.reproduction.obs_loop import (  # noqa: E402
    OBS_LOOP_POLICY_NAME,
    ObsLoopError,
)
from speech_aware_evidence_acquisition.reproduction.ojw import OJW_POLICY_NAME  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.ojw.components import (  # noqa: E402
    FrozenCoreASR,
)

from test_obs_loop_policy import (  # noqa: E402
    RUN_ID,
    SAMPLE_ID,
    _World,
    _boundary_text,
    _concat,
    _config_values,
    _noise,
    _silence,
)


def _scenario(name):
    """(pcm, texts, values, evidence, arm) per scenario — every behavioural
    surface of the plain policy the ojw executor must reproduce."""

    if name == "model-tails":
        return dict(
            pcm=_noise(150.0),
            texts=[
                _boundary_text("First span one. First tail", 45),
                _boundary_text("Second span two. Second tail", 50),
                _boundary_text("Final span three.", 30),
            ],
            # 4000-char tail >= any stitched text here: every request payload
            # embeds the FULL accumulated span text, so payload equality pins
            # the accepted-span sequence directly.
            values=_config_values(obs_condition_tail_chars=4000),
        )
    if name == "vad-trim":
        return dict(
            pcm=_concat(_silence(10.0), _noise(55.0)),
            texts=[_boundary_text("Speech only.", 30)],
            values=_config_values(),
        )
    if name == "fixed-ablation":
        values = _config_values(
            obs_buffer_seconds=30,
            obs_min_advance_seconds=30,
            obs_max_advance_seconds=30,
            obs_fallback_advance_seconds=30,
            obs_silence_snap_seconds=0,
            obs_boundary_mode="fixed",
            obs_vad_trim_min_seconds=0,
        )
        values.pop("obs_boundary_prompt")
        return dict(
            pcm=_noise(75.0),
            texts=["span one", "span two", "span three"],
            values=values,
        )
    if name == "evidence-arm":
        item = EvidenceItem(
            evidence_id="conec/4000001",
            source_uri="conec://earnings21/contexts/4000001.txt",
            content="ACME Corp, Q3, John Smith",
            provenance={"lock_key": "conec", "relpath": "x", "sha256": "e" * 64},
        )
        return dict(
            pcm=_noise(90.0),
            texts=[_boundary_text("A. spill", 45), _boundary_text("B.", 10)],
            values=_config_values(obs_condition_tail_chars=400),
            evidence=[item],
            arm="fixed-legal-context",
        )
    if name == "rms-norm":
        return dict(
            pcm=_noise(40.0),
            texts=[_boundary_text("Quiet speech.", 20)],
            values=_config_values(obs_preprocess=["rms-norm"]),
        )
    if name == "fallback-boundary":
        return dict(
            pcm=_noise(90.0),
            texts=["no boundary line at all here.", _boundary_text("Tail end.", 10)],
            values=_config_values(),
        )
    raise AssertionError(name)


SCENARIOS = (
    "model-tails",
    "vad-trim",
    "fixed-ablation",
    "evidence-arm",
    "rms-norm",
    "fallback-boundary",
)


def _run(tmp_path, monkeypatch, policy_name, scenario):
    world = _World(
        tmp_path,
        monkeypatch,
        pcm=scenario["pcm"],
        texts=list(scenario["texts"]),
        values=dict(scenario["values"]),
        evidence=scenario.get("evidence"),
        arm=scenario.get("arm", "bare-core"),
    )
    outcome = POLICIES.resolve(policy_name).run_sample(world.ctx)
    return world, outcome


def _trace_records(world):
    raw = (world.run_dir / f"{RUN_ID}.trace.jsonl").read_text(encoding="utf-8")
    records = [json.loads(line) for line in raw.splitlines() if line]
    for record in records:
        payload = record.get("payload")
        if isinstance(payload, dict):
            payload.pop("latency_seconds", None)  # volatile (COST); defensive
    return records


def _derivation_bytes(world):
    return (world.run_dir / f"{RUN_ID}.obs-derivation.{SAMPLE_ID}.json").read_bytes()


def _accepted_spans(world, scenario):
    """Re-derive the accepted-span sequence from this world's own OBS trace
    records through the frozen pure functions (module docstring)."""

    obs = [
        record["payload"]
        for record in _trace_records(world)
        if record["record_id"].startswith("req-0001-i")
        and record["record_id"].endswith("/obs")
    ]
    obs.sort(key=lambda payload: payload["obs_iteration"])
    values = scenario["values"]
    spans = []
    for payload, text in zip(obs, list(scenario["texts"]), strict=True):
        if values.get("obs_boundary_mode", "model") == "model":
            transcript, _ = parse_boundary_response(text)
        else:
            transcript = text.strip()
        if payload["obs_final_window"] or values.get("obs_boundary_mode") == "fixed":
            accepted = transcript
        else:
            slice_seconds = (
                payload["obs_window_end_seconds"] - payload["obs_window_start_seconds"]
            )
            accepted, _ = accept_up_to_boundary(
                transcript, payload["obs_boundary_advance_seconds"] / slice_seconds
            )
        spans.append(accepted.strip())
    return spans


def _fingerprint(world, outcome):
    document = {
        "trace": _trace_records(world),
        "derivation": _derivation_bytes(world).decode("utf-8"),
        "outcome": dataclasses.asdict(outcome),
    }
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class TestEquivalence:
    @pytest.mark.parametrize("name", SCENARIOS)
    def test_ojw_reproduces_the_plain_policy(self, tmp_path, monkeypatch, name):
        scenario = _scenario(name)
        plain_world, plain_outcome = _run(
            tmp_path / "plain", monkeypatch, OBS_LOOP_POLICY_NAME, scenario
        )
        ojw_world, ojw_outcome = _run(
            tmp_path / "ojw", monkeypatch, OJW_POLICY_NAME, scenario
        )
        # accepted-span sequences
        assert _accepted_spans(ojw_world, scenario) == _accepted_spans(
            plain_world, scenario
        )
        # every request payload (slice relpaths, metered seconds, rendered
        # instruction incl. boundary template + tail, evidence fields)
        assert ojw_world.adapter.payloads == plain_world.adapter.payloads
        # slice derivation records, byte for byte
        assert _derivation_bytes(ojw_world) == _derivation_bytes(plain_world)
        # written slice bytes
        for payload in plain_world.adapter.payloads:
            relpath = payload["media_relpath"]
            assert (ojw_world.data_root / relpath).read_bytes() == (
                plain_world.data_root / relpath
            ).read_bytes()
        # stitched output text + the full outputs-row shape
        assert ojw_outcome == plain_outcome
        # the complete trace record sequence (OBS incl. trims, stitch, USE)
        assert _trace_records(ojw_world) == _trace_records(plain_world)

    def test_stitched_text_and_registry_state(self, tmp_path, monkeypatch):
        scenario = _scenario("model-tails")
        ojw_world, ojw_outcome = _run(tmp_path, monkeypatch, OJW_POLICY_NAME, scenario)
        assert ojw_outcome.text == "First span one. Second span two. Final span three."
        assert ojw_outcome.request_ids == (
            "req-0001-i0000",
            "req-0001-i0001",
            "req-0001-i0002",
        )
        for payload in ojw_world.adapter.payloads:
            record = ojw_world.registry.lookup(SAMPLE_ID, payload["media_relpath"])
            assert record is not None
            assert record.parent_sha256


class TestDeterminism:
    def test_determinism_five_runs(self, tmp_path, monkeypatch):
        """Five fresh executor runs over the same fixture must be
        byte-identical (and identical to the plain reference) — the
        empirical check behind the linear-chain determinism argument."""

        scenario = _scenario("model-tails")
        plain_world, plain_outcome = _run(
            tmp_path / "plain", monkeypatch, OBS_LOOP_POLICY_NAME, scenario
        )
        reference = _fingerprint(plain_world, plain_outcome)
        fingerprints = []
        for index in range(5):
            world, outcome = _run(
                tmp_path / f"ojw{index}", monkeypatch, OJW_POLICY_NAME, scenario
            )
            fingerprints.append(_fingerprint(world, outcome))
        assert fingerprints == [reference] * 5


class TestSingleDoor:
    def test_frozen_core_asr_requires_an_injected_callable(self):
        with pytest.raises(ObsLoopError, match="callable adapter request"):
            FrozenCoreASR(adapter_request=None, state=None)
