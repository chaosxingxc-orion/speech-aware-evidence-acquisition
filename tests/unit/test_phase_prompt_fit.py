"""Zero-contact tests for ``scripts/a2t_calibration_prompt_fit.py --phase-program``
(E1.3): the exact prompt fit of a multi-contact phase program.

A phase program's request is not the adapter's one-contact prompt -- each
phase carries its own instruction on the payload's Agent-history CONTROL
turn -- so a cell whose select phase pastes the 152-tool registry and whose
fill phase does not has two envelopes thousands of tokens apart.
``FlightRuntime._assess_prompt_budget`` only ESTIMATES them; this mode
measures them on the resident server's own template and tokenizer.

Nothing here starts a server. The measurement path is driven through a fake
transport that mimics exactly the two routes the script calls
(``POST /apply-template`` and ``POST /tokenize``) and the single opaque media
marker ``GET /props`` reports; the envelopes it measures are REAL ones,
rendered through ``core.flight.runtime.render_phase_prompt_envelopes`` --
the same function ``FlightRuntime._verify_phase_prompt_fit`` re-renders with
at pre-flight time, so what this file exercises is what a flight verifies.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight.runtime import (
    phase_envelope_sha256,
    render_phase_prompt_envelopes,
)
from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact
from speech_aware_evidence_acquisition.rails.phase_material import PhaseMaterialSpec

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "a2t_calibration_prompt_fit.py"
MEDIA_MARKER = "<__media__>"
PACKET = {"packet_id": "a2t/tier1/000001", "sha256": "a" * 64}


def _script():
    """Load the measurement script, honouring its own two import guards.

    The script refuses to run against a package resolved from anywhere but
    its own checkout; when that is not this tree (a bare ``pytest`` with the
    shared editable install pointing elsewhere) the tests below would be
    exercising some other tree's code, so they skip rather than pretend.
    """

    import speech_aware_evidence_acquisition as package

    package_path = Path(package.__file__ or "").resolve()
    if package_path != (REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py"):
        pytest.skip(f"package resolves to {package_path}, not this checkout ({REPO})")
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    entries = [entry for entry in os.environ.get("PYTHONPATH", "").split(":") if entry]
    if str(REPO / "src") not in entries:
        os.environ["PYTHONPATH"] = ":".join([str(REPO / "src"), *entries])
    name = "_test_a2t_phase_prompt_fit_module"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# A fake resident server: the two routes the script calls, nothing else.
# ---------------------------------------------------------------------------


class _FakeServer:
    """Renders a prompt the way a chat template would -- system text, then
    the user content with the speech-feature part replaced by ONE opaque
    media marker -- and tokenizes on whitespace."""

    def __init__(self) -> None:
        self.apply_template_bodies: list[dict] = []
        self.tokenize_calls = 0

    def request_json(self, method: str, path: str, body):
        if method == "GET" and path == "/props":
            return {
                "media_marker": MEDIA_MARKER,
                "default_generation_settings": {"n_ctx": 65536},
                "chat_template": "fake-template",
            }
        if method == "POST" and path == "/apply-template":
            self.apply_template_bodies.append(body)
            return {"prompt": self._render(body)}
        if method == "POST" and path == "/tokenize":
            self.tokenize_calls += 1
            return {"tokens": str(body["content"]).split()}
        raise AssertionError(f"unexpected request {method} {path}")

    @staticmethod
    def _render(body) -> str:
        pieces: list[str] = []
        for tool in body.get("tools") or []:
            pieces.append(str(tool["function"]["name"]))
        for message in body["messages"]:
            content = message["content"]
            if isinstance(content, str):
                pieces.append(content)
                continue
            for part in content:
                if part.get("type") == "input_speech_features":
                    pieces.append(MEDIA_MARKER)
                else:
                    pieces.append(str(part.get("text", "")))
        return " ".join(pieces)


# ---------------------------------------------------------------------------
# A synthetic two-phase plan, built from REAL envelopes.
# ---------------------------------------------------------------------------


def _specs(*, per_sample_fill: bool) -> dict[str, PhaseMaterialSpec]:
    return {
        "select": PhaseMaterialSpec(
            phase="select",
            purpose="select-ordered-tool-occurrences",
            instruction_template="probes/select.txt",
            instruction_fill="audio2tool-registry-compact",
            predecessor_binding="none",
        ).validate(),
        "fill": PhaseMaterialSpec(
            phase="fill",
            purpose="fill-locked-selected-occurrences",
            instruction_template="probes/fill.txt",
            predecessor_binding=(
                "sealed-manifest" if per_sample_fill else "none"
            ),
            predecessor_source=(
                {
                    "manifest_relpath": "runs/prior/manifest.json",
                    "manifest_sha256": "b" * 64,
                    "producer_policy_id": "phase-select-then-fill-v1",
                }
                if per_sample_fill
                else None
            ),
        ).validate(),
    }


def _state(sample_id: str, content: str) -> AgentStateArtifact:
    return AgentStateArtifact(
        state_id=f"fill:{sample_id}",
        state_kind="phase:fill",
        content=content,
        source_query_state_sha256="c" * 64,
        source_response_sha256="d" * 64,
        producer_policy_id="phase-select-then-fill-v1",
        cited_value_ids=(),
    ).validate()


def _plan(tmp_path: Path, *, per_sample_fill: bool = False, sample_count: int = 3) -> dict:
    specs = _specs(per_sample_fill=per_sample_fill)
    static_text = {
        "select": "Select the tools.\n- setLighting(deviceId: String): Turns a light on.",
        "fill": "Fill the arguments.",
    }
    sample_ids = tuple(f"a2t:tier1:{index:06d}" for index in range(1, sample_count + 1))
    sealed = (
        {
            "fill": {
                sample_id: _state(sample_id, " ".join(["word"] * (index + 1)))
                for index, sample_id in enumerate(sample_ids)
            }
        }
        if per_sample_fill
        else {}
    )
    by_phase: dict[str, dict[str, str]] = {"select": {}, "fill": {}}
    envelopes_by_sha: dict[str, list] = {}
    for sample_id in sample_ids:
        rendered = render_phase_prompt_envelopes(
            program_id="phase-select-then-fill-v1",
            phase_names=("select", "fill"),
            specs=specs,
            static_text_by_phase=static_text,
            system_text="You control tools.",
            prompt_order="speech-query-prefix-v2",
            packet_descriptor=PACKET,
            sample_id=sample_id,
            sealed_states_by_phase=sealed,
            completion_token_ceiling=256,
        )
        for phase, envelope in rendered.items():
            digest = phase_envelope_sha256(envelope)
            by_phase[phase][sample_id] = digest
            envelopes_by_sha.setdefault(digest, list(envelope))

    promotion_path = tmp_path / "promotion.json"
    promotion = {
        "schema": "saea-a2t-speech-packet-promotion-receipt-v1",
        "feature_root": str(tmp_path / "features"),
        "legacy_cache_dir": str(tmp_path / "cache"),
        "runtime_receipt_sha256": "e" * 64,
        "packets": [
            {
                "packet_id": sample_id.replace(":", "/"),
                "packet_sha256": f"{index:064d}",
                "n_tokens": 100 + index,
            }
            for index, sample_id in enumerate(sample_ids)
        ],
    }
    promotion_path.write_text(json.dumps(promotion), encoding="utf-8")

    return {
        "cell_id": "KU-A2-select-then-fill",
        "arm": "speech-feature-query",
        "policy": "phase-select-then-fill-v1",
        "program_id": "phase-select-then-fill-v1",
        "model_fragment": "m",
        "dataset_fragment": "d",
        "baseline_fragment": "b",
        "experiment_fragment": "e",
        "config_hash": "f" * 64,
        "carrier_lock_key": "audio2tool",
        "split_id": "discovery",
        "prompt_order": "speech-query-prefix-v2",
        "specs": specs,
        "static_text": static_text,
        "sample_ids": sample_ids,
        "promotion_path": promotion_path,
        "promotion": promotion,
        "tool_schema_fill": None,
        "tools": None,
        "slots": 3,
        "slot_tokens": 22016,
        "completion_token_ceiling": 256,
        "phase_sha256_by_sample": by_phase,
        "envelopes_by_sha256": envelopes_by_sha,
    }


def _args(**overrides) -> SimpleNamespace:
    defaults = dict(
        reference_media_marker=None,
        speech_token_source="promotion",
        speech_window_tokens=13,
        speech_token_rule_reference_receipt=None,
        speech_token_rule_reference_roster=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _measure(module, plan, *, args=None):
    server = _FakeServer()
    counts = {"GET /props": 0, "POST /apply-template": 0, "POST /tokenize": 0, "generations": 0}
    measured = module.measure_phase_envelopes(
        server,
        [plan],
        media_marker=MEDIA_MARKER,
        counts=counts,
        args=args if args is not None else _args(),
    )
    return server, counts, measured


# ---------------------------------------------------------------------------
# The measurement path.
# ---------------------------------------------------------------------------


def test_the_script_writes_the_schema_the_runtime_verifies():
    module = _script()
    assert module.PHASE_PROMPT_FIT_SCHEMA == "saea-phase-prompt-fit-v1"


def test_every_contact_of_the_program_is_measured_exactly_once(tmp_path):
    """A phase envelope carries the contact id and the sample's own packet
    descriptor, so it is per-sample by construction: two phases over three
    samples are six contacts and six apply-template renders, one each --
    measured, never extrapolated from a representative."""

    module = _script()
    plan = _plan(tmp_path)
    server, counts, measured = _measure(module, plan)

    assert len(plan["envelopes_by_sha256"]) == 6
    assert counts["POST /apply-template"] == 6
    assert len(server.apply_template_bodies) == 6
    assert set(measured) == set(plan["envelopes_by_sha256"])
    for record in measured.values():
        assert record["text_prompt_tokens"] > 0
        assert len(record["rendered_prompt_sha256"]) == 64
    # The select phase carries the registry line; it must be the larger one.
    select_digest = plan["phase_sha256_by_sample"]["select"][plan["sample_ids"][0]]
    fill_digest = plan["phase_sha256_by_sample"]["fill"][plan["sample_ids"][0]]
    assert (
        measured[select_digest]["text_prompt_tokens"]
        > measured[fill_digest]["text_prompt_tokens"]
    )


def test_the_media_part_is_one_opaque_marker_in_every_measured_prompt(tmp_path):
    module = _script()
    plan = _plan(tmp_path)
    server, counts, _ = _measure(module, plan)

    for body in server.apply_template_bodies:
        prompt = _FakeServer._render(body)
        assert prompt.count(MEDIA_MARKER) == 1
    # One tokenize call per non-empty segment around the single marker.
    assert counts["POST /tokenize"] == 2 * len(server.apply_template_bodies)


def test_a_prompt_that_loses_its_media_marker_is_refused(tmp_path):
    """``text_token_count``'s own guard: a template that dropped or doubled
    the media part is not the prompt a flight sends, and a token count taken
    around it would be certifying the wrong envelope."""

    module = _script()
    plan = _plan(tmp_path)

    class _MarkerlessServer(_FakeServer):
        @staticmethod
        def _render(body) -> str:
            return "no media here"

    with pytest.raises(SystemExit, match="media markers"):
        module.measure_phase_envelopes(
            _MarkerlessServer(),
            [plan],
            media_marker=MEDIA_MARKER,
            counts={"POST /apply-template": 0, "POST /tokenize": 0},
            args=_args(),
        )


def test_a_reference_marker_records_the_nonce_free_prompt_hash(tmp_path):
    module = _script()
    plan = _plan(tmp_path)
    _, _, measured = _measure(module, plan, args=_args(reference_media_marker="<REF>"))

    for record in measured.values():
        assert record["reference_media_marker"] == "<REF>"
        assert (
            record["rendered_prompt_sha256_with_reference_marker"]
            != record["rendered_prompt_sha256"]
        )


# ---------------------------------------------------------------------------
# The per-phase report.
# ---------------------------------------------------------------------------


def test_the_report_names_the_max_sample_and_pins_its_envelope(tmp_path):
    """The maximum is what a flight is certified against, so the receipt has
    to say which sample attains it and pin THAT envelope's bytes -- that hash
    is what ``FlightRuntime._verify_phase_prompt_fit`` re-renders."""

    module = _script()
    plan = _plan(tmp_path, per_sample_fill=True)
    _, counts, measured = _measure(module, plan)
    row = module.phase_cell_rows(
        plan, measured, {sample_id: 500 for sample_id in plan["sample_ids"]}, reserve=8192
    )

    assert row["cell_id"] == "KU-A2-select-then-fill"
    assert [phase["phase"] for phase in row["phases"]] == ["select", "fill"]
    select, fill = row["phases"]

    # The select phase's static text does not vary, so every sample's
    # envelope differs only by its own contact id and packet descriptor and
    # the measured distribution is flat.
    assert select["distinct_envelopes"] == len(plan["sample_ids"])
    assert select["predecessor_binding"] == "none"
    assert select["exact_envelope"] is True
    assert select["text_prompt_tokens"]["min"] == select["text_prompt_tokens"]["max"]

    # The fill phase binds a sealed-manifest predecessor, so its instruction
    # is genuinely per-sample and the LAST sample carries the longest state.
    assert fill["distinct_envelopes"] == len(plan["sample_ids"])
    assert fill["predecessor_binding"] == "sealed-manifest"
    assert fill["max_sample_id"] == plan["sample_ids"][-1]
    assert fill["envelope_sha256"] == plan["phase_sha256_by_sample"]["fill"][
        fill["max_sample_id"]
    ]
    assert fill["text_prompt_tokens"]["max"] > fill["text_prompt_tokens"]["min"]
    for key in ("count", "min", "median", "p95", "max"):
        assert key in fill["text_prompt_tokens"]

    # The required window is the measured text plus the measured speech plus
    # the registered reserve plus the completion ceiling, per sample.
    assert fill["worst_required_window_tokens"] == (
        fill["max_text_prompt_tokens"] + 500 + module.SPECIAL_TOKEN_RESERVE + 256
    )
    assert row["worst_phase"] in {"select", "fill"}
    assert row["every_request_fits"] is True
    assert row["meets_reserve"] is True
    assert counts["POST /apply-template"] == 2 * len(plan["sample_ids"])


def test_a_cell_that_does_not_fit_its_slot_says_so(tmp_path):
    module = _script()
    plan = _plan(tmp_path)
    plan["slot_tokens"] = 32
    _, _, measured = _measure(module, plan)
    row = module.phase_cell_rows(
        plan, measured, {sample_id: 500 for sample_id in plan["sample_ids"]}, reserve=8192
    )

    assert row["every_request_fits"] is False
    assert row["meets_reserve"] is False
    assert all(phase["every_request_fits"] is False for phase in row["phases"])


# ---------------------------------------------------------------------------
# The registered contact allowance.
# ---------------------------------------------------------------------------


def test_the_allowance_is_one_render_per_contact_the_flight_makes(tmp_path):
    module = _script()
    plan = _plan(tmp_path)
    allowance = module.phase_contact_allowance([plan])

    assert allowance["phases"] == 2
    assert allowance["samples"] == 3
    assert allowance["program_contacts"] == 6
    assert allowance["apply_template_calls_allowed"] == 6
    assert allowance["distinct_envelopes"] == 6
    assert allowance["within_allowance"] is True


def test_material_that_varies_outside_phase_and_sample_is_refused(tmp_path):
    """The allowance is also the invariant: a program cannot render more
    distinct envelopes than it makes contacts. If it does, its material
    depends on something the receipt cannot name, and no per-sample maximum
    would be a bound."""

    module = _script()
    plan = _plan(tmp_path, per_sample_fill=True)
    # Two extra envelopes nothing accounts for.
    plan["envelopes_by_sha256"]["0" * 64] = []
    plan["envelopes_by_sha256"]["1" * 64] = []

    with pytest.raises(SystemExit, match="cannot be certified"):
        module.phase_contact_allowance([plan])


# ---------------------------------------------------------------------------
# Packet bindings and speech tokens.
# ---------------------------------------------------------------------------


def test_packet_bindings_are_the_descriptors_the_transport_carries(tmp_path):
    module = _script()
    plan = _plan(tmp_path)
    bindings = module.phase_packet_bindings(plan["promotion"], plan["sample_ids"])

    assert set(bindings) == set(plan["sample_ids"])
    first = plan["sample_ids"][0]
    assert bindings[first] == {"packet_id": first.replace(":", "/"), "sha256": "0" * 64}


def test_an_uncovered_sample_refuses_the_whole_measurement(tmp_path):
    module = _script()
    plan = _plan(tmp_path)
    with pytest.raises(SystemExit, match="no promoted packet"):
        module.phase_packet_bindings(plan["promotion"], (*plan["sample_ids"], "a2t:tier1:999999"))


def test_speech_tokens_come_from_the_promotion_receipts_own_counts(tmp_path):
    module = _script()
    plan = _plan(tmp_path)
    by_sample, record = module.phase_speech_tokens(plan, _args())

    assert by_sample == {
        sample_id: 100 + index for index, sample_id in enumerate(plan["sample_ids"])
    }
    assert record["source"] == str(plan["promotion_path"])
    assert len(record["source_sha256"]) == 64
    assert record["distribution"]["count"] == len(plan["sample_ids"])
