"""NX programme E1: the flight half -- pinned templates are hashed before contact.

``FlightRuntime._template_variant_materials`` turns a template group's pinned
``{relpath, sha256}`` declarations into per-arm material builders. It must read
the file, refuse a missing file or a digest other than the declared one, render
the text through the node's own fill, refuse text that embeds protected
knowledge payloads, and publish the resolved pins into the phase-material
receipt -- all before any contact.
"""

from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    FlightRuntimeError,
)
from speech_aware_evidence_acquisition.rails.phase_material import PhaseMaterialSpec
from speech_aware_evidence_acquisition.rails.supply_variants import parse_template_variants

FIT = {
    "slot_tokens": 24576, "completion_ceiling": 640,
    "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120,
}
LOCKED = "probes/slurp_native_role_solver_v2.txt"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _setup(tmp_path, *, texts=None, declared=None):
    texts = texts or {"t1": "template one body\n", "t2": "template two body\n"}
    probes = tmp_path / "configs" / "probes" / "nx"
    probes.mkdir(parents=True)
    for name, text in texts.items():
        (probes / f"{name}.txt").write_text(text, encoding="utf-8", newline="\n")
    declared = declared or {name: _sha(text) for name, text in texts.items()}
    group = parse_template_variants(
        {
            "node": "solver", "max_supplied_items": 4, "fit_estimate": dict(FIT),
            "arms": [
                {"arm_id": name, "template_tokens": 100,
                 "instruction_template": {
                     "relpath": f"configs/probes/nx/{name}.txt", "sha256": declared[name]}}
                for name in texts
            ] + [{"arm_id": "lock", "deliver": True, "template_tokens": 90}],
        },
        role_kind="solver", phase_id="solver", locked_template=LOCKED,
    )
    fake_self = SimpleNamespace(
        _repo_root=tmp_path, _lock={}, _data_root=tmp_path, _phase_material_receipt=None,
    )
    calls = []

    def material_with_static_text(overrides):
        calls.append(dict(overrides))
        return lambda phase, context, sealed: ("material", dict(overrides))

    spec = PhaseMaterialSpec(phase="solver", purpose="answer", instruction_template=LOCKED)
    binding = {
        "material_with_static_text": material_with_static_text,
        "phase_specs": {"solver": spec},
        "protected_material": ("secret-key-text",),
    }
    native_config = SimpleNamespace(supply_variant_group=group, supply_variant_phase_id="solver")
    return fake_self, native_config, binding, calls


def _call(fake_self, native_config, binding):
    return FlightRuntime._template_variant_materials(fake_self, native_config, None, binding)


def test_pinned_templates_become_per_arm_builders_and_a_receipt(tmp_path):
    fake_self, config, binding, calls = _setup(tmp_path)
    builders = _call(fake_self, config, binding)
    assert set(builders) == {"t1", "t2"}  # the delivering arm gets none
    assert calls == [{"solver": "template one body\n"}, {"solver": "template two body\n"}]
    receipt = fake_self._phase_material_receipt["template_variants"]
    assert receipt["t1"] == {
        "relpath": "probes/nx/t1.txt", "sha256": _sha("template one body\n"),
        "rendered_sha256": _sha("template one body\n"),
    }
    assert builders["t2"]("solver", None, {})[1] == {"solver": "template two body\n"}


def test_a_template_whose_bytes_differ_from_the_declared_digest_is_refused(tmp_path):
    fake_self, config, binding, _ = _setup(
        tmp_path, declared={"t1": "e" * 64, "t2": _sha("template two body\n")},
    )
    with pytest.raises(FlightRuntimeError, match="hashes to .* not the declared"):
        _call(fake_self, config, binding)


def test_a_missing_template_file_is_refused(tmp_path):
    fake_self, config, binding, _ = _setup(tmp_path)
    (tmp_path / "configs" / "probes" / "nx" / "t2.txt").unlink()
    with pytest.raises(FlightRuntimeError, match="is missing"):
        _call(fake_self, config, binding)


def test_a_template_embedding_protected_knowledge_is_refused(tmp_path):
    text = "template one body mentions SECRET-KEY-TEXT here\n"
    fake_self, config, binding, _ = _setup(
        tmp_path, texts={"t1": text, "t2": "template two body\n"},
    )
    with pytest.raises(FlightRuntimeError, match="embeds frozen knowledge"):
        _call(fake_self, config, binding)


def test_an_empty_template_is_refused_by_the_renderer(tmp_path):
    from speech_aware_evidence_acquisition.rails.phase_material import PhaseMaterialError

    fake_self, config, binding, _ = _setup(tmp_path, texts={"t1": "  \n", "t2": "ok\n"})
    with pytest.raises(PhaseMaterialError, match="is empty"):
        _call(fake_self, config, binding)


def test_a_config_without_a_template_group_binds_nothing(tmp_path):
    fake_self, _config, binding, _ = _setup(tmp_path)
    assert _call(
        fake_self, SimpleNamespace(supply_variant_group=None, perception_branch_group=None), binding,
    ) is None
    assert _call(fake_self, None, binding) is None
    assert fake_self._phase_material_receipt is None


def test_a_flight_that_published_no_builder_is_refused(tmp_path):
    fake_self, config, binding, _ = _setup(tmp_path)
    binding.pop("material_with_static_text")
    with pytest.raises(FlightRuntimeError, match="material builder"):
        _call(fake_self, config, binding)
