"""E1 config seam: a phase program's per-phase material, from config alone.

``rails.controllers.EvidenceAgentController`` has always taken its per-phase
instruction and response format from an injected
``material_for_phase(phase_name, context)`` callable, and
``rails.phase_runner.run_program`` from the richer
``material_for_phase(phase_name, context, sealed_states)``. Nothing built
either from config, so every multi-contact cell needed a launcher script to
hand-write one -- which is exactly the fragmentation the owner's 2026-09-03
"one base, thin derivations" rule forbids, and why
``core.flight.FlightRuntime.bind_phase_program_material`` had no callers at
all.

This module is that missing builder. A baseline fragment declares

.. code-block:: json

    "phase_material": {
      "select": {
        "instruction_template": "probes/a2t_phase_select.txt",
        "instruction_fill": "audio2tool-registry-compact",
        "response_format_id": "select-response-v1"
      },
      "fill": {
        "instruction_template": "probes/a2t_phase_fill.txt",
        "predecessor_binding": "append-sealed-state"
      }
    }

and :func:`load_phase_material_specs` turns it into one
:class:`PhaseMaterialSpec` per phase of the program, fail-closed against the
program's own ``PhaseSpec`` list. Identity is the same as every other
instruction in this study: the config hash pins the template PATH and the
fill NAME, ``configs/probes/manifest.json`` pins the template BYTES, and the
umbrella lock pins the carrier data the fill reads.

Three things this module deliberately does NOT do:

* it never ranks, retrieves or fuses evidence (that is ``rails.supply`` /
  ``rails.kb_policy``, reached through ``supply_for_phase``);
* it never reads gold, and never reads the adapter's sample object -- the
  material callable sees only ``rails.runner.AgentRuntimeContext``;
* it never writes the system message. The system message is
  ``adapter.instruction(sample)`` plus the adapter's task contract, assembled
  by ``rails.runner._agent_messages``; a phase's instruction rides the
  payload ``history`` CONTROL turn (``rails.core_client._agent_history``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

from ..core.base import RESPONSE_FORMATS
from ..core.instructions import (
    TOOL_SCHEMAS_PLACEHOLDER,
    _TEMPLATE_RELPATH_PATTERN,
    render_template_with_fill,
)
from .controllers import PhaseProgram
from .errors import RailsError
from .knowledge import AgentStateArtifact
from .material import PhaseMaterial

#: How a phase's instruction is conditioned on what ran before it.
#:
#: ``"none"``      -- the rendered static text, and nothing else.
#: ``"append-sealed-state"`` -- append THIS run's immediately preceding
#:                    phase's sealed ``AgentStateArtifact`` for the same
#:                    sample (``run_program`` threads it in as
#:                    ``sealed_states``).
#: ``"sealed-manifest"`` -- append a state rebuilt from an ALREADY SEALED
#:                    bundle of a different run (see
#:                    :func:`sealed_states_from_manifest`). This is how a
#:                    slot-stage cell conditions on the sealed closed-list
#:                    intent without re-flying the contact that produced it.
PREDECESSOR_BINDINGS = frozenset({"none", "append-sealed-state", "sealed-manifest"})

_SPEC_KEYS = frozenset(
    {
        "instruction_template",
        "instruction_fill",
        "fill_params",
        "response_format_id",
        "predecessor_binding",
        "predecessor_source",
    }
)
_PREDECESSOR_SOURCE_KEYS = frozenset(
    {"manifest_relpath", "manifest_sha256", "producer_policy_id"}
)

#: The exact prefix an appended predecessor state carries. Fixed here rather
#: than made configurable: a two-contact cell's paired contrast is only a
#: single-factor contrast if this framing is the same in every arm.
PREDECESSOR_PREFIX = "Prior phase response"


class PhaseMaterialError(RailsError):
    """A ``phase_material`` config fragment, or the material built from it,
    is invalid."""


@dataclass(frozen=True)
class PhaseMaterialSpec:
    """One phase's config-declared material, before rendering."""

    phase: str
    purpose: str
    instruction_template: str
    instruction_fill: str | None = None
    fill_params: Mapping[str, object] = field(default_factory=dict)
    response_format_id: str | None = None
    predecessor_binding: str = "none"
    predecessor_source: Mapping[str, object] | None = None

    def validate(self) -> "PhaseMaterialSpec":
        for name in ("phase", "purpose", "instruction_template"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise PhaseMaterialError(
                    f"PhaseMaterialSpec.{name} must be a non-empty string"
                )
        if not _TEMPLATE_RELPATH_PATTERN.fullmatch(self.instruction_template):
            raise PhaseMaterialError(
                f"phase {self.phase!r} instruction_template "
                f"{self.instruction_template!r} is not a plain relative path under "
                "configs/ (no absolute paths, no '..', no backslashes)"
            )
        if self.instruction_fill is not None and (
            not isinstance(self.instruction_fill, str) or not self.instruction_fill.strip()
        ):
            raise PhaseMaterialError(
                f"phase {self.phase!r} instruction_fill must be a non-empty string or null"
            )
        if not isinstance(self.fill_params, Mapping):
            raise PhaseMaterialError(
                f"phase {self.phase!r} fill_params must be an object"
            )
        if self.fill_params and self.instruction_fill is None:
            raise PhaseMaterialError(
                f"phase {self.phase!r} declares fill_params but no instruction_fill"
            )
        if self.response_format_id is not None and (
            not isinstance(self.response_format_id, str)
            or not self.response_format_id.strip()
        ):
            raise PhaseMaterialError(
                f"phase {self.phase!r} response_format_id must be a non-empty string "
                "or null"
            )
        if self.predecessor_binding not in PREDECESSOR_BINDINGS:
            raise PhaseMaterialError(
                f"phase {self.phase!r} predecessor_binding must be one of "
                f"{sorted(PREDECESSOR_BINDINGS)}, got {self.predecessor_binding!r}"
            )
        if self.predecessor_binding == "sealed-manifest":
            source = self.predecessor_source
            if not isinstance(source, Mapping) or set(source) != _PREDECESSOR_SOURCE_KEYS:
                raise PhaseMaterialError(
                    f"phase {self.phase!r} predecessor_binding 'sealed-manifest' requires "
                    f"a predecessor_source object with exactly "
                    f"{sorted(_PREDECESSOR_SOURCE_KEYS)}"
                )
            for key in sorted(_PREDECESSOR_SOURCE_KEYS):
                if not isinstance(source[key], str) or not source[key].strip():
                    raise PhaseMaterialError(
                        f"phase {self.phase!r} predecessor_source.{key} must be a "
                        "non-empty string"
                    )
        elif self.predecessor_source is not None:
            raise PhaseMaterialError(
                f"phase {self.phase!r} declares predecessor_source but its "
                f"predecessor_binding is {self.predecessor_binding!r}"
            )
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "phase": self.phase,
            "purpose": self.purpose,
            "instruction_template": self.instruction_template,
            "instruction_fill": self.instruction_fill,
            "fill_params": dict(self.fill_params),
            "response_format_id": self.response_format_id,
            "predecessor_binding": self.predecessor_binding,
            "predecessor_source": (
                dict(self.predecessor_source)
                if self.predecessor_source is not None
                else None
            ),
        }


def load_phase_material_specs(
    values: Mapping[str, object], program: PhaseProgram
) -> Mapping[str, PhaseMaterialSpec]:
    """Parse the baseline fragment's ``phase_material`` object against
    ``program``.

    Refuses: a missing or non-object ``phase_material``; a phase the program
    does not declare; a program phase with no material; an unknown key in a
    phase entry; and any disagreement between a phase's declared
    ``response_format_id`` and the program's own ``PhaseSpec`` -- both
    present and equal, or both absent, nothing in between (the same rule
    ``EvidenceAgentController._dispatch`` enforces at contact time, moved
    forward to config-load time where it is free).
    """

    program.validate()
    declared = values.get("phase_material")
    if not isinstance(declared, Mapping) or not declared:
        raise PhaseMaterialError(
            f"policy {program.program_id!r} is a phase program; its baseline fragment "
            "must declare a non-empty 'phase_material' object keyed by phase name "
            f"({list(program.phase_names())})"
        )
    known = set(program.phase_names())
    unknown = sorted(set(declared) - known)
    if unknown:
        raise PhaseMaterialError(
            f"phase_material names phase(s) {unknown} that program "
            f"{program.program_id!r} does not declare; its phases are "
            f"{sorted(known)}"
        )
    missing = sorted(known - set(declared))
    if missing:
        raise PhaseMaterialError(
            f"phase_material has no entry for program {program.program_id!r} phase(s) "
            f"{missing}; every phase must declare its own material"
        )

    specs: dict[str, PhaseMaterialSpec] = {}
    for phase in program.phases:
        entry = declared[phase.name]
        if not isinstance(entry, Mapping):
            raise PhaseMaterialError(
                f"phase_material[{phase.name!r}] must be an object"
            )
        extra = sorted(set(entry) - _SPEC_KEYS)
        if extra:
            raise PhaseMaterialError(
                f"phase_material[{phase.name!r}] carries unknown key(s) {extra}; "
                f"known keys are {sorted(_SPEC_KEYS)}"
            )
        spec = PhaseMaterialSpec(
            phase=phase.name,
            purpose=phase.purpose,
            instruction_template=entry.get("instruction_template"),
            instruction_fill=entry.get("instruction_fill"),
            fill_params=dict(entry.get("fill_params") or {}),
            response_format_id=entry.get("response_format_id"),
            predecessor_binding=str(entry.get("predecessor_binding", "none")),
            predecessor_source=entry.get("predecessor_source"),
        ).validate()
        if spec.response_format_id != phase.response_format_id:
            raise PhaseMaterialError(
                f"phase {phase.name!r} declares response_format_id "
                f"{phase.response_format_id!r} in program {program.program_id!r} but "
                f"{spec.response_format_id!r} in phase_material; a phase's output "
                "contract has exactly one authority"
            )
        specs[phase.name] = spec
    return specs


def render_static_instruction(
    spec: PhaseMaterialSpec, repo_root: Path, lock: Mapping[str, object], root: Path
) -> str:
    """The phase's sample-independent instruction text.

    With an ``instruction_fill`` this is ``core.instructions.
    render_template_with_fill`` -- the same frozen-template-plus-registered-
    fill path every baseline ``task_instruction_template`` already uses,
    with ``fill_params`` passed as keyword arguments only when non-empty.
    Without one it is the template's own bytes, and a template that still
    carries the ``{tool_schemas}`` placeholder is refused rather than sent
    half-rendered.
    """

    spec.validate()
    if spec.instruction_fill is not None:
        return render_template_with_fill(
            spec.instruction_template,
            spec.instruction_fill,
            repo_root,
            lock,
            root,
            spec.fill_params,
        )
    template_path = Path(repo_root) / "configs" / spec.instruction_template
    if not template_path.is_file():
        raise PhaseMaterialError(f"phase instruction template missing: {template_path}")
    try:
        text = template_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise PhaseMaterialError(
            f"cannot read phase instruction template {template_path}: {error}"
        ) from error
    if TOOL_SCHEMAS_PLACEHOLDER in text:
        raise PhaseMaterialError(
            f"phase {spec.phase!r} template {template_path} carries a "
            f"{TOOL_SCHEMAS_PLACEHOLDER!r} placeholder but the phase declares no "
            "instruction_fill; an unfilled template must never reach the model"
        )
    if not text.strip():
        raise PhaseMaterialError(
            f"phase {spec.phase!r} template {template_path} is empty"
        )
    return text


def resolve_response_formats(
    specs: Mapping[str, PhaseMaterialSpec], lock: Mapping[str, object], root: Path
) -> Mapping[str, Mapping[str, object]]:
    """``{phase: response_format}`` for every phase that declares a
    ``response_format_id``, resolved through ``core.base.RESPONSE_FORMATS``
    (a ``(lock, root, **params) -> Mapping`` thunk registered in
    ``rails.controllers``). Phases without an id contribute no entry."""

    formats: dict[str, Mapping[str, object]] = {}
    for phase, spec in specs.items():
        if spec.response_format_id is None:
            continue
        builder = RESPONSE_FORMATS.resolve(spec.response_format_id)
        if not callable(builder):
            raise PhaseMaterialError(
                f"registered response format {spec.response_format_id!r} is not callable"
            )
        document = builder(lock, root, **dict(spec.fill_params))
        if not isinstance(document, Mapping) or not document:
            raise PhaseMaterialError(
                f"response format {spec.response_format_id!r} rendered an empty result "
                f"for phase {phase!r}"
            )
        formats[phase] = document
    return formats


def _appended(instruction: str, state: AgentStateArtifact) -> str:
    return (
        f"{instruction}\n\n{PREDECESSOR_PREFIX} ({state.state_kind}):\n{state.content}"
    )


def build_material_for_phase(
    specs: Mapping[str, PhaseMaterialSpec],
    *,
    program_id: str,
    static_text_by_phase: Mapping[str, str],
    response_format_by_phase: Mapping[str, Mapping[str, object]],
    per_sample_states: Mapping[str, Mapping[str, AgentStateArtifact]] | None = None,
):
    """Build the ``rails.phase_runner.ProgramMaterialForPhase`` callable.

    ``(phase_name, context, sealed_states) -> PhaseMaterial``. The
    instruction is the phase's already-rendered static text, plus -- under
    ``append-sealed-state`` -- this run's immediately preceding phase's
    sealed state for THIS sample, or -- under ``sealed-manifest`` -- the
    state ``per_sample_states[phase][sample_id]`` rebuilt from another run's
    sealed bundle. ``contact_id`` is ``"{program_id}:{phase}:{sample_id}"``,
    the same shape ``rails.controllers._default_material_for_phase`` mints.

    Fail-closed on every missing piece: an unknown phase, a sample with no
    predecessor state, a phase whose response format was not resolved. All
    of them would otherwise become a silently weaker prompt on the wire.
    """

    if not isinstance(program_id, str) or not program_id:
        raise PhaseMaterialError("build_material_for_phase requires a program_id")
    states = dict(per_sample_states or {})

    def material_for_phase(
        phase_name: str,
        context: object,
        sealed_states: Mapping[str, AgentStateArtifact],
    ) -> PhaseMaterial:
        try:
            spec = specs[phase_name]
        except KeyError:
            raise PhaseMaterialError(
                f"no phase material for phase {phase_name!r}; known phases are "
                f"{sorted(specs)}"
            ) from None
        sample_id = getattr(context, "sample_id", None)
        if not isinstance(sample_id, str) or not sample_id:
            raise PhaseMaterialError(
                "material_for_phase needs an AgentRuntimeContext carrying a sample_id"
            )
        try:
            instruction = static_text_by_phase[phase_name]
        except KeyError:
            raise PhaseMaterialError(
                f"phase {phase_name!r} has no rendered instruction text"
            ) from None

        if spec.predecessor_binding == "append-sealed-state":
            state = (sealed_states or {}).get(sample_id)
            if state is None:
                raise PhaseMaterialError(
                    f"phase {phase_name!r} binds its predecessor's sealed state but the "
                    f"preceding phase sealed none for sample {sample_id!r}"
                )
            instruction = _appended(instruction, state)
        elif spec.predecessor_binding == "sealed-manifest":
            state = states.get(phase_name, {}).get(sample_id)
            if state is None:
                raise PhaseMaterialError(
                    f"phase {phase_name!r} binds a sealed-manifest predecessor but no "
                    f"state was loaded for sample {sample_id!r}"
                )
            instruction = _appended(instruction, state)

        response_format = response_format_by_phase.get(phase_name)
        if (spec.response_format_id is not None) != (response_format is not None):
            raise PhaseMaterialError(
                f"phase {phase_name!r} declares response_format_id "
                f"{spec.response_format_id!r} but "
                f"{'no' if response_format is None else 'a'} response format was "
                "resolved for it"
            )
        return PhaseMaterial(
            instruction=instruction,
            response_format=response_format,
            contact_id=f"{program_id}:{phase_name}:{sample_id}",
            purpose=spec.purpose,
        ).validate()

    return material_for_phase


def sealed_states_from_manifest(
    manifest_path: Path,
    *,
    expected_sha256: str,
    phase_name: str,
    producer_policy_id: str,
    sample_ids: Sequence[str],
    bundle_verifier=None,
) -> Mapping[str, AgentStateArtifact]:
    """Rebuild ``{sample_id: AgentStateArtifact}`` from an ALREADY SEALED
    bundle.

    This is how a later cell conditions on a sealed predecessor answer -- the
    SLURP slot stage on the sealed closed-list intent, say -- without
    re-flying the contact that produced it, and without inventing the
    provenance: the state's two source hashes are the sealed row's own
    ``request_sha256``/``response_text_sha256``, so the artifact is bound to
    the exact bytes the frozen core actually answered with.

    Fail-closed on a manifest whose bytes do not hash to ``expected_sha256``,
    on any requested sample the bundle does not carry, and on anything
    ``core.bundle.verify_bundle`` itself refuses.
    """

    from ..core.bundle.verify import verify_bundle  # noqa: PLC0415 (cycle guard)

    verifier = bundle_verifier if bundle_verifier is not None else verify_bundle
    manifest_path = Path(manifest_path)
    import hashlib  # noqa: PLC0415 (used only here)

    digest = hashlib.sha256()
    try:
        with manifest_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
    except OSError as error:
        raise PhaseMaterialError(
            f"cannot read sealed predecessor manifest {manifest_path}: {error}"
        ) from error
    measured = digest.hexdigest()
    if measured != expected_sha256:
        raise PhaseMaterialError(
            f"sealed predecessor manifest {manifest_path} hashes to {measured}, not the "
            f"configured {expected_sha256}"
        )

    verified = verifier(manifest_path)
    by_sample: dict[str, Mapping[str, object]] = {}
    for row in verified.outputs_rows:
        sample_id = str(row.get("sample_id"))
        if sample_id in by_sample:
            raise PhaseMaterialError(
                f"sealed predecessor manifest {manifest_path} carries duplicate rows "
                f"for sample {sample_id!r}"
            )
        by_sample[sample_id] = row

    wanted = tuple(sample_ids)
    missing = sorted(set(wanted) - set(by_sample))
    if missing:
        raise PhaseMaterialError(
            f"sealed predecessor manifest {manifest_path} has no row for "
            f"{len(missing)} requested sample(s), e.g. {missing[:5]}"
        )
    states: dict[str, AgentStateArtifact] = {}
    for sample_id in wanted:
        row = by_sample[sample_id]
        states[sample_id] = AgentStateArtifact(
            state_id=f"{phase_name}:{sample_id}",
            state_kind=f"phase:{phase_name}",
            content=str(row["text"]),
            source_query_state_sha256=str(row["request_sha256"]),
            source_response_sha256=str(row["response_text_sha256"]),
            producer_policy_id=producer_policy_id,
            cited_value_ids=(),
        ).validate()
    return states


def render_phase_envelope(
    system_text: str,
    instruction: str,
    *,
    prompt_order: str,
    packet_descriptor: Mapping[str, object],
    contact_id: str,
    agent_state: Sequence[Mapping[str, object]] = (),
) -> tuple[Mapping[str, object], ...]:
    """The EXACT transport message pair one phase contact crosses the wire as.

    Lifted verbatim from ``rails.probes.a2t_select_fill_agentloop.
    render_phase_request`` lines 781-828 (the ``feature`` part, the
    ``_agent_history`` call, ``_speech_history_texts``,
    ``_ordered_speech_feature_content`` with empty ``evidence_texts`` and
    empty ``knowledge_roles``, ``_assert_agent_history_suffix``, and the
    ``(system, user)`` tuple built from the result) rather than imported
    from it: that module is a probe, scheduled for disposal, and the owner
    rule forbids new code depending on ``rails/probes/``. A unit test pins
    byte equality against the probe's own function for the same inputs for
    as long as the probe exists.

    Nothing here talks to a server. This is the preflight/wire-check view of
    a contact: ``rails.core_client.FrozenCoreClient`` assembles the identical
    shape at request time from ``agent_state``/``agent_contact_id``/
    ``contact_instruction``.
    """

    from ..core.model import FrozenCoreError  # noqa: PLC0415 (cycle guard)
    from ..core.model.transport import (  # noqa: PLC0415 (cycle guard)
        _assert_agent_history_suffix,
        _ordered_speech_feature_content,
        _speech_history_texts,
    )
    from .core_client import _agent_history  # noqa: PLC0415 (cycle guard)

    if not isinstance(system_text, str) or not system_text:
        raise PhaseMaterialError("render_phase_envelope requires a system message")
    if not isinstance(packet_descriptor, Mapping) or set(packet_descriptor) != {
        "packet_id",
        "sha256",
    }:
        raise PhaseMaterialError(
            "packet_descriptor must carry exactly packet_id and sha256"
        )
    feature = {
        "type": "input_speech_features",
        "speech_features": {
            "packet_id": packet_descriptor["packet_id"],
            "sha256": packet_descriptor["sha256"],
            "role": "query",
        },
    }
    history = list(
        _agent_history(
            agent_state=tuple(agent_state),
            agent_contact_id=contact_id,
            contact_instruction=instruction,
        )
    )
    try:
        state_texts = _speech_history_texts(history)
        ordered_content = _ordered_speech_feature_content(
            prompt_order=prompt_order,
            evidence_texts=[],
            feature_parts=[feature],
            state_texts=state_texts,
            knowledge_roles=(),
        )
        _assert_agent_history_suffix(
            prompt_order=prompt_order,
            content=ordered_content,
            state_texts=state_texts,
        )
    except FrozenCoreError as error:
        raise PhaseMaterialError(
            f"unsupported or invalid transport prompt order: {error}"
        ) from error
    return (
        {"role": "system", "content": system_text},
        {"role": "user", "content": ordered_content},
    )


def phase_material_receipt(
    specs: Mapping[str, PhaseMaterialSpec],
    static_text_by_phase: Mapping[str, str],
    response_format_by_phase: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    """A hashable identity record for what this run's phase material is --
    the spec plus the rendered instruction's length and sha256 plus the
    response format's sha256, per phase. Never the instruction text itself:
    it can be the whole 152-tool registry."""

    import hashlib  # noqa: PLC0415 (used only here)

    phases: list[Mapping[str, object]] = []
    for phase in sorted(specs):
        text = static_text_by_phase[phase]
        document = response_format_by_phase.get(phase)
        phases.append(
            {
                "spec": specs[phase].as_json(),
                "instruction_chars": len(text),
                "instruction_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "response_format_sha256": (
                    hashlib.sha256(
                        json.dumps(document, sort_keys=True, ensure_ascii=False).encode(
                            "utf-8"
                        )
                    ).hexdigest()
                    if document is not None
                    else None
                ),
            }
        )
    return {"schema": "saea-phase-material-v1", "phases": phases}


__all__ = [
    "PREDECESSOR_BINDINGS",
    "PREDECESSOR_PREFIX",
    "PhaseMaterialError",
    "PhaseMaterialSpec",
    "build_material_for_phase",
    "load_phase_material_specs",
    "phase_material_receipt",
    "render_phase_envelope",
    "render_static_instruction",
    "resolve_response_formats",
    "sealed_states_from_manifest",
]
