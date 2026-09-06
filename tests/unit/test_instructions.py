"""Task-instruction resolution seam (P1 scaffold + E3b fill parameters).

A baseline fragment supplies EITHER a literal ``task_instruction`` (every
pre-existing fragment, byte-identical behavior) OR a frozen template
reference (``task_instruction_template`` under ``configs/`` +
``task_instruction_fill`` naming a registered ``INSTRUCTION_FILLS`` entry)
whose single supported ``{tool_schemas}`` placeholder is rendered at run
time from pinned carrier data — never committed into Git.

E3b (2026-09-05) adds an optional ``task_instruction_fill_params`` object of
NAMED arguments for a fill that declares them, and the first such fill:
``evolved-artifact-v1``, which renders the released compact registry with a
hash-pinned artifact's description overrides applied. The tests below hold
both halves of the contract: the four pre-existing fills keep resolving
exactly as before (no keyword argument reaches them), and every way the new
key or the new fill can be wrong is refused.
"""

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.base import INSTRUCTION_FILLS, CoreError
from speech_aware_evidence_acquisition.core.instructions import (
    EVOLVED_FILL_NAME,
    TOOL_SCHEMAS_PLACEHOLDER,
    _fill_call_kwargs,
    _fill_parameter_shape,
    render_evolved_registry,
    resolve_active_task_instruction,
    resolve_task_instruction,
)
from speech_aware_evidence_acquisition.data.audio2tool import (
    load_tool_registry,
    render_tool_schemas,
)
from speech_aware_evidence_acquisition.data.audio2tool_tools import (
    render_registry_compact,
)
from speech_aware_evidence_acquisition.data.lock import load_lock


def test_literal_task_instruction_passes_through(tmp_path):
    values = {"task_instruction": "Transcribe."}
    assert resolve_task_instruction(values, tmp_path, {}, tmp_path) == "Transcribe."


def test_literal_and_template_together_are_refused(tmp_path):
    values = {"task_instruction": "x", "task_instruction_template": "probes/t.txt"}
    with pytest.raises(CoreError, match="both"):
        resolve_task_instruction(values, tmp_path, {}, tmp_path)


def test_neither_literal_nor_template_is_refused(tmp_path):
    with pytest.raises(CoreError, match="task_instruction"):
        resolve_task_instruction({}, tmp_path, {}, tmp_path)


def test_template_renders_the_registered_fill(audio2tool_world):
    lock = load_lock(audio2tool_world.lock_path)
    values = {
        "task_instruction_template": audio2tool_world.template_relpath,
        "task_instruction_fill": "audio2tool-tool-schemas",
    }
    rendered = resolve_task_instruction(
        values, audio2tool_world.repo_root, lock, audio2tool_world.data_root
    )
    assert TOOL_SCHEMAS_PLACEHOLDER not in rendered
    assert '"tool_name": "setLighting"' in rendered
    assert '"tool_name": "setSecurityMode"' in rendered
    assert rendered.startswith("You control tools.")


def test_template_without_fill_is_refused(audio2tool_world):
    values = {"task_instruction_template": audio2tool_world.template_relpath}
    with pytest.raises(CoreError, match="task_instruction_fill"):
        resolve_task_instruction(
            values, audio2tool_world.repo_root, {}, audio2tool_world.data_root
        )


def test_template_missing_placeholder_is_refused(audio2tool_world, tmp_path):
    template = audio2tool_world.repo_root / "configs" / "probes" / "noslot.txt"
    template.write_text("no placeholder here\n", encoding="utf-8")
    lock = load_lock(audio2tool_world.lock_path)
    values = {
        "task_instruction_template": "probes/noslot.txt",
        "task_instruction_fill": "audio2tool-tool-schemas",
    }
    with pytest.raises(CoreError, match="placeholder"):
        resolve_task_instruction(
            values, audio2tool_world.repo_root, lock, audio2tool_world.data_root
        )


def test_template_path_traversal_is_refused(audio2tool_world):
    values = {
        "task_instruction_template": "../secrets.txt",
        "task_instruction_fill": "audio2tool-tool-schemas",
    }
    with pytest.raises(CoreError, match="template"):
        resolve_task_instruction(
            values, audio2tool_world.repo_root, {}, audio2tool_world.data_root
        )


def test_missing_template_file_is_refused(audio2tool_world):
    values = {
        "task_instruction_template": "probes/absent.txt",
        "task_instruction_fill": "audio2tool-tool-schemas",
    }
    with pytest.raises(CoreError, match="template"):
        resolve_task_instruction(
            values, audio2tool_world.repo_root, {}, audio2tool_world.data_root
        )


def test_unknown_fill_name_is_refused(audio2tool_world):
    values = {
        "task_instruction_template": audio2tool_world.template_relpath,
        "task_instruction_fill": "no-such-fill",
    }
    with pytest.raises(CoreError, match="no-such-fill"):
        resolve_task_instruction(
            values, audio2tool_world.repo_root, {}, audio2tool_world.data_root
        )


def test_audio2tool_fill_is_registered():
    assert "audio2tool-tool-schemas" in INSTRUCTION_FILLS.names()


# ---------------------------------------------------------------------------
# E3b: task_instruction_fill_params and the evolved-artifact-v1 fill.
#
# The pre-existing fills carry the byte-identity burden: every one of them
# must still be called as exactly ``fill(lock, root)``, because that is what
# every sealed cell's rendered instruction was produced by.
# ---------------------------------------------------------------------------

PRE_EXISTING_FILLS = (
    "audio2tool-tool-schemas",
    "audio2tool-registry-compact",
    "audio2tool-registry-grouped",
    "slurp-label-inventory",
    "slurp-intent-slot-schema",
)


def test_the_pre_existing_fills_are_called_with_no_keyword_arguments(tmp_path):
    """Byte identity, stated as the property that produces it: with no
    params declared, the resolver computes an EMPTY keyword mapping for every
    fill that existed before E3b, so ``render_template_with_fill`` takes its
    ``fill(lock, root)`` branch exactly as before."""

    for name in PRE_EXISTING_FILLS:
        fill = INSTRUCTION_FILLS.resolve(name)
        assert _fill_call_kwargs(fill, name, None, tmp_path) == {}
        assert _fill_call_kwargs(fill, name, {}, tmp_path) == {}
        # None of them declares repo_root, so nothing is injected either.
        accepted, required, _ = _fill_parameter_shape(fill)
        assert "repo_root" not in accepted
        assert required == frozenset()


def test_template_rendering_is_byte_identical_to_manual_substitution(audio2tool_world):
    """End-to-end byte identity on the synthetic registry: the resolved
    instruction equals the frozen template with the fill's own output
    substituted, for both registry fills, with the params key absent."""

    lock = load_lock(audio2tool_world.lock_path)
    template = (
        audio2tool_world.repo_root / "configs" / audio2tool_world.template_relpath
    ).read_text(encoding="utf-8")
    for name, renderer in (
        ("audio2tool-tool-schemas", render_tool_schemas),
        ("audio2tool-registry-compact", render_registry_compact),
    ):
        rendered = resolve_task_instruction(
            {
                "task_instruction_template": audio2tool_world.template_relpath,
                "task_instruction_fill": name,
            },
            audio2tool_world.repo_root,
            lock,
            audio2tool_world.data_root,
        )
        assert rendered == template.replace(
            TOOL_SCHEMAS_PLACEHOLDER, renderer(lock, audio2tool_world.data_root)
        )


def test_params_on_a_params_less_fill_are_refused(audio2tool_world):
    values = {
        "task_instruction_template": audio2tool_world.template_relpath,
        "task_instruction_fill": "audio2tool-tool-schemas",
        "task_instruction_fill_params": {"artifact_relpath": "configs/x.json"},
    }
    with pytest.raises(CoreError, match="accepts no fill parameters"):
        resolve_task_instruction(
            values,
            audio2tool_world.repo_root,
            load_lock(audio2tool_world.lock_path),
            audio2tool_world.data_root,
        )


def test_non_object_fill_params_are_refused(audio2tool_world):
    values = {
        "task_instruction_template": audio2tool_world.template_relpath,
        "task_instruction_fill": "audio2tool-tool-schemas",
        "task_instruction_fill_params": ["artifact_relpath"],
    }
    with pytest.raises(CoreError, match="must be a JSON object"):
        resolve_task_instruction(
            values, audio2tool_world.repo_root, {}, audio2tool_world.data_root
        )


def test_fill_params_beside_a_literal_instruction_are_refused(tmp_path):
    values = {
        "task_instruction": "Transcribe.",
        "task_instruction_fill_params": {"artifact_relpath": "configs/x.json"},
    }
    with pytest.raises(CoreError, match="beside a literal"):
        resolve_task_instruction(values, tmp_path, {}, tmp_path)


def test_fill_params_may_not_name_an_injected_argument(audio2tool_world):
    values = {
        "task_instruction_template": audio2tool_world.template_relpath,
        "task_instruction_fill": EVOLVED_FILL_NAME,
        "task_instruction_fill_params": {
            "repo_root": "/elsewhere",
            "artifact_relpath": "configs/a.json",
            "artifact_sha256": "0" * 64,
        },
    }
    with pytest.raises(CoreError, match="reserved argument"):
        resolve_task_instruction(
            values,
            audio2tool_world.repo_root,
            load_lock(audio2tool_world.lock_path),
            audio2tool_world.data_root,
        )


def test_a_required_fill_parameter_that_is_missing_is_refused(audio2tool_world):
    values = {
        "task_instruction_template": audio2tool_world.template_relpath,
        "task_instruction_fill": EVOLVED_FILL_NAME,
        "task_instruction_fill_params": {"artifact_relpath": "configs/a.json"},
    }
    with pytest.raises(CoreError, match="requires fill parameter"):
        resolve_task_instruction(
            values,
            audio2tool_world.repo_root,
            load_lock(audio2tool_world.lock_path),
            audio2tool_world.data_root,
        )


# -- the evolved-artifact-v1 fill itself ------------------------------------


def _write_artifact(repo_root: Path, overrides: dict, *, relpath: str) -> tuple[str, str]:
    """Write ``overrides`` exactly as ``rails.evolution`` writes it (canonical
    JSON bytes) and return ``(relpath, sha256)``."""

    from speech_aware_evidence_acquisition.rails.hashing import canonical_json_bytes

    path = repo_root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_bytes(overrides)
    path.write_bytes(payload)
    return relpath, hashlib.sha256(payload).hexdigest()


def test_evolved_fill_is_registered_under_the_name_evolution_writes(audio2tool_world):
    from speech_aware_evidence_acquisition.rails import evolution

    assert EVOLVED_FILL_NAME == evolution.EVOLVED_FILL_NAME == "evolved-artifact-v1"
    assert EVOLVED_FILL_NAME in INSTRUCTION_FILLS.names()
    assert INSTRUCTION_FILLS.resolve(EVOLVED_FILL_NAME) is render_evolved_registry


def test_evolved_fill_applies_the_override_and_changes_nothing_else(audio2tool_world):
    lock = load_lock(audio2tool_world.lock_path)
    relpath, sha256 = _write_artifact(
        audio2tool_world.repo_root,
        {"setLighting": "A replacement description."},
        relpath="configs/evolved/registry.json",
    )
    rendered = render_evolved_registry(
        lock,
        audio2tool_world.data_root,
        repo_root=audio2tool_world.repo_root,
        artifact_relpath=relpath,
        artifact_sha256=sha256,
    )
    baseline = render_registry_compact(lock, audio2tool_world.data_root).split("\n")
    evolved = rendered.split("\n")
    assert len(evolved) == len(baseline)
    differing = [i for i in range(len(baseline)) if baseline[i] != evolved[i]]
    assert len(differing) == 1
    assert evolved[differing[0]].endswith(": A replacement description.")
    assert evolved[differing[0]].split(":")[0] == baseline[differing[0]].split(":")[0]


def test_evolved_fill_refuses_a_hash_mismatch(audio2tool_world):
    lock = load_lock(audio2tool_world.lock_path)
    relpath, sha256 = _write_artifact(
        audio2tool_world.repo_root,
        {"setLighting": "First."},
        relpath="configs/evolved/registry.json",
    )
    # Edit the artifact after its fragment was emitted.
    (audio2tool_world.repo_root / relpath).write_text(
        json.dumps({"setLighting": "Second."}), encoding="utf-8"
    )
    with pytest.raises(CoreError, match="hashes to"):
        render_evolved_registry(
            lock,
            audio2tool_world.data_root,
            repo_root=audio2tool_world.repo_root,
            artifact_relpath=relpath,
            artifact_sha256=sha256,
        )


@pytest.mark.parametrize(
    "relpath, match",
    [
        ("../secrets.json", "plain relative path"),
        ("configs/../../secrets.json", "plain relative path"),
        ("/etc/passwd", "plain relative path"),
        ("configs\\evolved\\registry.json", "plain relative path"),
        ("docs/receipts/registry.json", "not under configs/"),
    ],
)
def test_evolved_fill_refuses_a_relative_path_escape(audio2tool_world, relpath, match):
    with pytest.raises(CoreError, match=match):
        render_evolved_registry(
            load_lock(audio2tool_world.lock_path),
            audio2tool_world.data_root,
            repo_root=audio2tool_world.repo_root,
            artifact_relpath=relpath,
            artifact_sha256="0" * 64,
        )


def test_evolved_fill_refuses_an_empty_or_unknown_override(audio2tool_world):
    lock = load_lock(audio2tool_world.lock_path)
    empty_rel, empty_sha = _write_artifact(
        audio2tool_world.repo_root, {}, relpath="configs/evolved/empty.json"
    )
    with pytest.raises(CoreError, match="non-empty JSON object"):
        render_evolved_registry(
            lock,
            audio2tool_world.data_root,
            repo_root=audio2tool_world.repo_root,
            artifact_relpath=empty_rel,
            artifact_sha256=empty_sha,
        )
    bad_rel, bad_sha = _write_artifact(
        audio2tool_world.repo_root,
        {"noSuchTool": "x"},
        relpath="configs/evolved/unknown.json",
    )
    with pytest.raises(Exception, match="not a tools_registry.csv tool"):
        render_evolved_registry(
            lock,
            audio2tool_world.data_root,
            repo_root=audio2tool_world.repo_root,
            artifact_relpath=bad_rel,
            artifact_sha256=bad_sha,
        )


def test_evolved_fill_refuses_a_missing_artifact(audio2tool_world):
    with pytest.raises(CoreError, match="evolved artifact missing"):
        render_evolved_registry(
            load_lock(audio2tool_world.lock_path),
            audio2tool_world.data_root,
            repo_root=audio2tool_world.repo_root,
            artifact_relpath="configs/evolved/absent.json",
            artifact_sha256="0" * 64,
        )


# -- the loop closed: a fragment rails.evolution wrote, resolved end to end --


def _evolution_fragment(repo_root: Path, template_relpath: str, overrides: dict) -> dict:
    """Emit one candidate baseline fragment exactly as ``rails.evolution.
    write_candidate_fragments`` does, with its artifact under ``configs/``."""

    from speech_aware_evidence_acquisition.rails.evolution import (
        Portfolio,
        write_candidate_fragments,
    )
    from speech_aware_evidence_acquisition.rails.hashing import content_hash

    portfolio = Portfolio(
        round=1,
        k=2,
        overrides=dict(overrides),
        candidate_ids={"T1": "cand-1"},
        portfolio_sha256=content_hash(dict(overrides)),
    )
    written = write_candidate_fragments(
        [portfolio],
        base_fragment={
            "arm": "bare-core-direct",
            "policy": "fixed",
            "task_instruction_template": template_relpath,
            "task_instruction_template_active": True,
        },
        out_dir=repo_root / "configs" / "baseline",
        artifact_dir=repo_root / "configs" / "evolved",
        artifact_relpath_base=repo_root,
    )
    return json.loads(written[0].read_text(encoding="utf-8"))


def test_an_evolution_written_fragment_resolves_through_the_active_resolver(
    audio2tool_world,
):
    lock = load_lock(audio2tool_world.lock_path)
    fragment = _evolution_fragment(
        audio2tool_world.repo_root,
        audio2tool_world.template_relpath,
        {"setSecurityMode": "Evolved: arms or disarms the house."},
    )
    assert fragment["task_instruction_fill"] == EVOLVED_FILL_NAME
    params = fragment["task_instruction_fill_params"]
    assert params["artifact_relpath"].startswith("configs/evolved/")
    # The writer records round/k/portfolio provenance in the SAME object; the
    # resolver must pass the two named arguments and treat the rest as
    # provenance rather than refusing the fragment it wrote.
    assert {"portfolio_sha256", "round", "k"} <= set(params)

    rendered = resolve_active_task_instruction(
        fragment, audio2tool_world.repo_root, lock, audio2tool_world.data_root
    )
    assert TOOL_SCHEMAS_PLACEHOLDER not in rendered
    assert "Evolved: arms or disarms the house." in rendered
    assert "Turns a light on." in rendered  # the untargeted row is untouched


# -- the real 152-row registry, when this host carries it --------------------


def _real_lock_and_root():
    from speech_aware_evidence_acquisition.data.audio2tool import AUDIO2TOOL_LOCK_KEY
    from speech_aware_evidence_acquisition.data.lock import (
        AssetResolutionError,
        asset_dir,
        data_root,
        umbrella_lock_path,
    )

    try:
        root = data_root()
        lock = load_lock(umbrella_lock_path())
        carrier_dir = asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root)
        if not (carrier_dir / "tools_registry.csv").is_file():
            return None
        return lock, root
    except (AssetResolutionError, OSError):
        return None


_REAL = _real_lock_and_root()


@pytest.mark.skipif(_REAL is None, reason="real audio2tool registry not available on this host")
def test_an_evolution_written_fragment_renders_a_152_line_registry(tmp_path):
    lock, root = _REAL
    repo_root = tmp_path / "repo"
    template_relpath = "probes/evolved.txt"
    template = repo_root / "configs" / template_relpath
    template.parent.mkdir(parents=True, exist_ok=True)
    template.write_text(
        "You control tools.\n\n## Available Tools:\n{tool_schemas}\n", encoding="utf-8"
    )
    victim = sorted(row["tool_name"] for row in load_tool_registry(lock, root))[0]
    fragment = _evolution_fragment(
        repo_root, template_relpath, {victim: "An evolved description."}
    )
    rendered = resolve_active_task_instruction(fragment, repo_root, lock, root)
    block = rendered.split("## Available Tools:\n", 1)[1].rstrip("\n")
    assert len(block.split("\n")) == 152
    baseline = render_registry_compact(lock, root).split("\n")
    evolved = block.split("\n")
    differing = [i for i in range(152) if baseline[i] != evolved[i]]
    assert len(differing) == 1
    assert evolved[differing[0]].endswith(": An evolved description.")
