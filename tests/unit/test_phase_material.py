"""Unit tests for ``rails.phase_material`` (E1 config seam).

Model-free throughout: no server, no GPU, no network. The one test that
touches another module's internals on purpose is
``test_render_phase_envelope_is_byte_identical_to_the_select_fill_probe`` --
it pins the lifted transport shape against the probe it was lifted from,
for as long as that probe exists.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.base import CoreError, RESPONSE_FORMATS
from speech_aware_evidence_acquisition.rails.controllers import (
    PhaseProgram,
    PhaseSpec,
    default_phase_program,
)
from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from speech_aware_evidence_acquisition.rails.phase_material import (
    PhaseMaterialError,
    PhaseMaterialSpec,
    build_material_for_phase,
    load_phase_material_specs,
    phase_material_receipt,
    render_phase_envelope,
    render_static_instruction,
    resolve_response_formats,
    sealed_states_from_manifest,
)

HASHES = {character: character * 64 for character in "123456789abcdef"}


def _program() -> PhaseProgram:
    return PhaseProgram(
        program_id="phase-select-then-fill-v1",
        phases=(
            PhaseSpec(
                name="select",
                purpose="select-tools",
                knowledge="none",
                response_format_id="select-response-v1",
                barrier=True,
            ),
            PhaseSpec(
                name="fill",
                purpose="fill-arguments",
                knowledge="none",
                response_format_id="fill-response-v1",
                barrier=False,
            ),
        ),
        max_contacts=2,
        stop_rule="always-run-full-program",
    ).validate()


def _values(**overrides: object) -> dict[str, object]:
    document: dict[str, object] = {
        "phase_material": {
            "select": {
                "instruction_template": "probes/select.txt",
                "instruction_fill": "audio2tool-registry-compact",
                "response_format_id": "select-response-v1",
            },
            "fill": {
                "instruction_template": "probes/fill.txt",
                "response_format_id": "fill-response-v1",
                "predecessor_binding": "append-sealed-state",
            },
        }
    }
    document.update(overrides)
    return document


def _state(sample_id: str, content: str = "prior answer") -> AgentStateArtifact:
    return AgentStateArtifact(
        state_id=f"select:{sample_id}",
        state_kind="phase:select",
        content=content,
        source_query_state_sha256=HASHES["1"],
        source_response_sha256=HASHES["2"],
        producer_policy_id="phase-select-then-fill-v1",
        cited_value_ids=(),
    ).validate()


def _context(sample_id: str = "s1") -> SimpleNamespace:
    return SimpleNamespace(sample_id=sample_id)


# ---------------------------------------------------------------------------
# load_phase_material_specs
# ---------------------------------------------------------------------------


def test_load_phase_material_specs_reads_every_phase_of_the_program():
    specs = load_phase_material_specs(_values(), _program())

    assert sorted(specs) == ["fill", "select"]
    assert specs["select"].purpose == "select-tools"
    assert specs["select"].instruction_fill == "audio2tool-registry-compact"
    assert specs["select"].predecessor_binding == "none"
    assert specs["fill"].predecessor_binding == "append-sealed-state"
    assert specs["fill"].instruction_fill is None


def test_load_phase_material_specs_refuses_a_missing_declaration():
    with pytest.raises(PhaseMaterialError, match="must declare a non-empty"):
        load_phase_material_specs({}, _program())


def test_load_phase_material_specs_refuses_a_phase_the_program_lacks():
    values = _values()
    values["phase_material"]["revise"] = {"instruction_template": "probes/x.txt"}
    with pytest.raises(PhaseMaterialError, match="does not declare"):
        load_phase_material_specs(values, _program())


def test_load_phase_material_specs_refuses_a_program_phase_without_material():
    values = _values()
    del values["phase_material"]["fill"]
    with pytest.raises(PhaseMaterialError, match="no entry for program"):
        load_phase_material_specs(values, _program())


def test_load_phase_material_specs_refuses_a_response_format_mismatch():
    values = _values()
    values["phase_material"]["select"]["response_format_id"] = None
    with pytest.raises(PhaseMaterialError, match="exactly one authority"):
        load_phase_material_specs(values, _program())


def test_load_phase_material_specs_refuses_an_unknown_key():
    values = _values()
    values["phase_material"]["select"]["supply_source"] = "kb"
    with pytest.raises(PhaseMaterialError, match="unknown key"):
        load_phase_material_specs(values, _program())


def test_phase_material_spec_refuses_an_escaping_template_path():
    with pytest.raises(PhaseMaterialError, match="plain relative path"):
        PhaseMaterialSpec(
            phase="select",
            purpose="p",
            instruction_template="../secrets.txt",
        ).validate()


def test_phase_material_spec_requires_a_full_sealed_manifest_source():
    with pytest.raises(PhaseMaterialError, match="predecessor_source"):
        PhaseMaterialSpec(
            phase="fill",
            purpose="p",
            instruction_template="probes/fill.txt",
            predecessor_binding="sealed-manifest",
        ).validate()
    with pytest.raises(PhaseMaterialError, match="predecessor_binding is"):
        PhaseMaterialSpec(
            phase="fill",
            purpose="p",
            instruction_template="probes/fill.txt",
            predecessor_source={
                "manifest_relpath": "r",
                "manifest_sha256": "s",
                "producer_policy_id": "p",
            },
        ).validate()


# ---------------------------------------------------------------------------
# render_static_instruction
# ---------------------------------------------------------------------------


def _repo_with_templates(tmp_path: Path) -> Path:
    probes = tmp_path / "configs" / "probes"
    probes.mkdir(parents=True)
    (probes / "plain.txt").write_text("Answer the phase.\n", encoding="utf-8")
    (probes / "filled.txt").write_text("Tools:\n{tool_schemas}\n", encoding="utf-8")
    (probes / "unfilled.txt").write_text("Tools:\n{tool_schemas}\n", encoding="utf-8")
    return tmp_path


def test_render_static_instruction_without_a_fill_returns_the_template_bytes(tmp_path):
    repo = _repo_with_templates(tmp_path)
    spec = PhaseMaterialSpec(
        phase="fill", purpose="p", instruction_template="probes/plain.txt"
    )
    assert render_static_instruction(spec, repo, {}, tmp_path) == "Answer the phase.\n"


def test_render_static_instruction_refuses_an_unfilled_placeholder(tmp_path):
    repo = _repo_with_templates(tmp_path)
    spec = PhaseMaterialSpec(
        phase="fill", purpose="p", instruction_template="probes/unfilled.txt"
    )
    with pytest.raises(PhaseMaterialError, match="never reach the model"):
        render_static_instruction(spec, repo, {}, tmp_path)


def test_render_static_instruction_refuses_a_missing_template(tmp_path):
    repo = _repo_with_templates(tmp_path)
    spec = PhaseMaterialSpec(
        phase="fill", purpose="p", instruction_template="probes/absent.txt"
    )
    with pytest.raises(PhaseMaterialError, match="template missing"):
        render_static_instruction(spec, repo, {}, tmp_path)


def test_render_static_instruction_goes_through_the_registered_fill(tmp_path, monkeypatch):
    repo = _repo_with_templates(tmp_path)
    calls: list[tuple] = []

    def _fake_fill(lock, root, **params):
        calls.append((lock, root, params))
        return "- a(): first"

    from speech_aware_evidence_acquisition.core import instructions

    monkeypatch.setattr(
        instructions.INSTRUCTION_FILLS, "resolve", lambda name: _fake_fill
    )
    spec = PhaseMaterialSpec(
        phase="select",
        purpose="p",
        instruction_template="probes/filled.txt",
        instruction_fill="fake-fill",
    )
    rendered = render_static_instruction(spec, repo, {"lock": True}, tmp_path)

    assert rendered == "Tools:\n- a(): first\n"
    # No fill_params -> the fill is called with the plain (lock, root) shape
    # every existing INSTRUCTION_FILLS entry uses.
    assert calls == [({"lock": True}, tmp_path, {})]


def test_render_static_instruction_passes_fill_params_as_keywords(tmp_path, monkeypatch):
    repo = _repo_with_templates(tmp_path)
    seen: list[dict] = []

    def _fake_fill(lock, root, **params):
        seen.append(params)
        return "filled"

    from speech_aware_evidence_acquisition.core import instructions

    monkeypatch.setattr(
        instructions.INSTRUCTION_FILLS, "resolve", lambda name: _fake_fill
    )
    spec = PhaseMaterialSpec(
        phase="select",
        purpose="p",
        instruction_template="probes/filled.txt",
        instruction_fill="fake-fill",
        fill_params={"max_calls": 3},
    )
    render_static_instruction(spec, repo, {}, tmp_path)
    assert seen == [{"max_calls": 3}]


def test_resolve_task_instruction_still_refuses_an_unknown_fill(tmp_path):
    """The factoring kept resolve_task_instruction's own behaviour: the
    refusal still comes from core.instructions and is still a CoreError."""

    from speech_aware_evidence_acquisition.core.instructions import (
        resolve_task_instruction,
    )

    repo = _repo_with_templates(tmp_path)
    with pytest.raises(CoreError, match="unknown instruction fill"):
        resolve_task_instruction(
            {
                "task_instruction_template": "probes/filled.txt",
                "task_instruction_fill": "no-such-fill",
            },
            repo,
            {},
            tmp_path,
        )


# ---------------------------------------------------------------------------
# build_material_for_phase
# ---------------------------------------------------------------------------


def _built(specs, **overrides):
    kwargs: dict[str, object] = {
        "program_id": "phase-select-then-fill-v1",
        "static_text_by_phase": {"select": "SELECT TEXT", "fill": "FILL TEXT"},
        "response_format_by_phase": {
            "select": {"type": "json_schema"},
            "fill": {"type": "json_schema"},
        },
    }
    kwargs.update(overrides)
    return build_material_for_phase(specs, **kwargs)


def test_build_material_for_phase_returns_the_static_text_for_a_first_phase():
    specs = load_phase_material_specs(_values(), _program())
    material = _built(specs)("select", _context(), {})

    assert isinstance(material, PhaseMaterial)
    assert material.instruction == "SELECT TEXT"
    assert material.contact_id == "phase-select-then-fill-v1:select:s1"
    assert material.purpose == "select-tools"
    assert material.response_format == {"type": "json_schema"}


def test_build_material_for_phase_appends_the_sealed_predecessor_state():
    specs = load_phase_material_specs(_values(), _program())
    material = _built(specs)("fill", _context(), {"s1": _state("s1")})

    assert material.instruction == (
        "FILL TEXT\n\nPrior phase response (phase:select):\nprior answer"
    )


def test_build_material_for_phase_fails_closed_on_a_missing_predecessor():
    specs = load_phase_material_specs(_values(), _program())
    with pytest.raises(PhaseMaterialError, match="sealed none for sample"):
        _built(specs)("fill", _context("s2"), {"s1": _state("s1")})


def test_build_material_for_phase_fails_closed_on_an_unknown_phase():
    specs = load_phase_material_specs(_values(), _program())
    with pytest.raises(PhaseMaterialError, match="no phase material"):
        _built(specs)("revise", _context(), {})


def test_build_material_for_phase_fails_closed_on_a_missing_response_format():
    specs = load_phase_material_specs(_values(), _program())
    with pytest.raises(PhaseMaterialError, match="response format was"):
        _built(specs, response_format_by_phase={})("select", _context(), {})


def test_build_material_for_phase_reads_a_sealed_manifest_predecessor():
    values = _values()
    values["phase_material"]["fill"] = {
        "instruction_template": "probes/fill.txt",
        "response_format_id": "fill-response-v1",
        "predecessor_binding": "sealed-manifest",
        "predecessor_source": {
            "manifest_relpath": "runs/x/y.run-manifest.json",
            "manifest_sha256": HASHES["a"],
            "producer_policy_id": "saea-earlier-cell-v1",
        },
    }
    specs = load_phase_material_specs(values, _program())
    material = _built(
        specs, per_sample_states={"fill": {"s1": _state("s1", "sealed intent")}}
    )("fill", _context(), {})

    assert material.instruction.endswith("sealed intent")


# ---------------------------------------------------------------------------
# sealed_states_from_manifest
# ---------------------------------------------------------------------------


def _manifest(tmp_path: Path, body: bytes = b'{"schema": "fake"}') -> Path:
    path = tmp_path / "run.run-manifest.json"
    path.write_bytes(body)
    return path


def _verified(rows):
    return SimpleNamespace(outputs_rows=tuple(rows))


def test_sealed_states_from_manifest_binds_the_sealed_response_hashes(tmp_path):
    path = _manifest(tmp_path)
    rows = [
        {
            "sample_id": "s1",
            "text": "sealed answer",
            "request_sha256": HASHES["3"],
            "response_text_sha256": HASHES["4"],
        }
    ]
    states = sealed_states_from_manifest(
        path,
        expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        phase_name="intent",
        producer_policy_id="saea-slurp-closed-list-direct-v1",
        sample_ids=("s1",),
        bundle_verifier=lambda _p: _verified(rows),
    )

    state = states["s1"]
    assert state.state_id == "intent:s1"
    assert state.state_kind == "phase:intent"
    assert state.content == "sealed answer"
    assert state.source_query_state_sha256 == HASHES["3"]
    assert state.source_response_sha256 == HASHES["4"]
    assert state.producer_policy_id == "saea-slurp-closed-list-direct-v1"


def test_sealed_states_from_manifest_refuses_a_hash_mismatch(tmp_path):
    path = _manifest(tmp_path)
    with pytest.raises(PhaseMaterialError, match="not the configured"):
        sealed_states_from_manifest(
            path,
            expected_sha256=HASHES["b"],
            phase_name="intent",
            producer_policy_id="p",
            sample_ids=("s1",),
            bundle_verifier=lambda _p: _verified([]),
        )


def test_sealed_states_from_manifest_refuses_a_missing_sample(tmp_path):
    path = _manifest(tmp_path)
    with pytest.raises(PhaseMaterialError, match="no row for"):
        sealed_states_from_manifest(
            path,
            expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            phase_name="intent",
            producer_policy_id="p",
            sample_ids=("s1", "s2"),
            bundle_verifier=lambda _p: _verified(
                [
                    {
                        "sample_id": "s1",
                        "text": "a",
                        "request_sha256": HASHES["3"],
                        "response_text_sha256": HASHES["4"],
                    }
                ]
            ),
        )


# ---------------------------------------------------------------------------
# response formats
# ---------------------------------------------------------------------------


def test_registered_response_format_ids_cover_the_select_then_fill_program():
    assert set(RESPONSE_FORMATS.names()) >= {"select-response-v1", "fill-response-v1"}
    program = default_phase_program("phase-select-then-fill-v1")
    for phase in program.phases:
        if phase.response_format_id is not None:
            assert phase.response_format_id in RESPONSE_FORMATS.names()


def test_resolve_response_formats_refuses_an_unregistered_id():
    specs = {
        "select": PhaseMaterialSpec(
            phase="select",
            purpose="p",
            instruction_template="probes/select.txt",
            response_format_id="no-such-format-v1",
        )
    }
    with pytest.raises(CoreError, match="unknown response format"):
        resolve_response_formats(specs, {}, Path("."))


def test_resolve_response_formats_skips_phases_without_an_id():
    specs = {
        "fill": PhaseMaterialSpec(
            phase="fill", purpose="p", instruction_template="probes/fill.txt"
        )
    }
    assert resolve_response_formats(specs, {}, Path(".")) == {}


# ---------------------------------------------------------------------------
# receipt
# ---------------------------------------------------------------------------


def test_phase_material_receipt_records_hashes_never_the_text():
    specs = load_phase_material_specs(_values(), _program())
    receipt = phase_material_receipt(
        specs,
        {"select": "SELECT TEXT", "fill": "FILL TEXT"},
        {"select": {"type": "json_schema"}},
    )

    assert receipt["schema"] == "saea-phase-material-v1"
    select = receipt["phases"][1]
    assert select["spec"]["phase"] == "select"
    assert select["instruction_chars"] == len("SELECT TEXT")
    assert select["instruction_sha256"] == hashlib.sha256(b"SELECT TEXT").hexdigest()
    assert select["response_format_sha256"] is not None
    assert receipt["phases"][0]["response_format_sha256"] is None
    assert "SELECT TEXT" not in json.dumps(receipt)


# ---------------------------------------------------------------------------
# render_phase_envelope: byte equality with the probe it was lifted from
# ---------------------------------------------------------------------------


def test_render_phase_envelope_is_byte_identical_to_the_select_fill_probe():
    """The transport shape was LIFTED, not imported (the owner rule forbids
    new code depending on rails/probes/). This pins the two together for as
    long as the probe exists; when the probe is disposed, so is this test."""

    from speech_aware_evidence_acquisition.rails.a2t_stage_state import (
        SelectOccurrence,
        build_select_stage_envelope,
    )
    from speech_aware_evidence_acquisition.rails.probes import (
        a2t_select_fill_agentloop as loop,
    )

    def _canonical(value: object) -> str:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )

    names = ("setTimer", "sendMessage", "getWeather")
    observation = _canonical(
        {"retrieval_query": "set a short timer", "transcript": "set a timer"}
    )
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "test_phase",
            "strict": True,
            "schema": {
                "type": "array",
                "minItems": 1,
                "maxItems": 7,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"enum": list(names)},
                        "arguments": {"type": "object"},
                    },
                    "required": ["name", "arguments"],
                    "additionalProperties": False,
                },
            },
        },
    }
    predecessor = build_select_stage_envelope(
        sample_identity_sha256=hashlib.sha256(b"fresh:000").hexdigest(),
        split_identity_sha256=HASHES["1"],
        speech_packet_sha256=HASHES["2"],
        source_query_state_sha256=HASHES["3"],
        source_response_sha256=HASHES["4"],
        observation_state_sha256=hashlib.sha256(
            _canonical(json.loads(observation)).encode("ascii")
        ).hexdigest(),
        observation_source_response_sha256=HASHES["5"],
        source_request_body_sha256=HASHES["6"],
        candidate_tool_names=names,
        ground_sha256=HASHES["7"],
        response_schema_sha256=HASHES["8"],
        predecessor_envelope_sha256=None,
        occurrences=(
            SelectOccurrence("occurrence-000", "setTimer"),
            SelectOccurrence("occurrence-001", "setTimer"),
        ),
    )
    ground = "ASCII FILL ground\n"
    material = loop.PhaseMaterial(
        sample_id="fresh:000",
        phase=loop.FILL_PHASE,
        candidate_tool_names=names,
        ground_text=ground,
        ground_sha256=hashlib.sha256(ground.encode("ascii")).hexdigest(),
        response_format=response_format,
        response_format_sha256=hashlib.sha256(
            _canonical(response_format).encode("ascii")
        ).hexdigest(),
        observation_state_json=observation,
        observation_state_sha256=hashlib.sha256(
            _canonical(json.loads(observation)).encode("ascii")
        ).hexdigest(),
        observation_source_response_sha256=HASHES["5"],
        predecessor=predecessor,
    )
    binding = {"packet_id": "packet:fresh:000", "sha256": HASHES["2"]}
    prompt_order = "speech-query-prefix-v2"

    probe_rendered = loop.render_phase_request(
        material, binding, prompt_order=prompt_order
    )
    lifted = render_phase_envelope(
        material.ground_text,
        loop._contact_instruction(material),
        prompt_order=prompt_order,
        packet_descriptor=binding,
        contact_id=loop._PHASE_CONTACT[material.phase],
    )

    assert lifted == probe_rendered.transport_messages
    assert json.dumps(lifted, sort_keys=True) == json.dumps(
        probe_rendered.transport_messages, sort_keys=True
    )


def test_render_phase_envelope_refuses_a_malformed_packet_descriptor():
    with pytest.raises(PhaseMaterialError, match="packet_id and sha256"):
        render_phase_envelope(
            "system",
            "instruction",
            prompt_order="speech-query-prefix-v2",
            packet_descriptor={"packet_id": "p"},
            contact_id="c",
        )


def test_render_phase_envelope_refuses_an_unknown_prompt_order():
    with pytest.raises(PhaseMaterialError, match="prompt order"):
        render_phase_envelope(
            "system",
            "instruction",
            prompt_order="no-such-order",
            packet_descriptor={"packet_id": "p", "sha256": HASHES["2"]},
            contact_id="c",
        )
