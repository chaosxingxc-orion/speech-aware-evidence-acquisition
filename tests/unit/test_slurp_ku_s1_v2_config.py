"""Cell KU-S1's composed configuration
(``configs/experiment/slurp-consumption-ku-s1-v2.json`` +
``configs/baseline/slurp-phase-blend-cl-v1.json``), round-tripped.

Two questions, and nothing else. **Does every component id the composed cell
names resolve in a ``core.base`` registry** -- the owner rule of 2026-09-03
that ``scripts/checks/engineering_base_check.py`` enforces over the config
tree, applied here through the real registries rather than a regex scan? And
**does the preflight accept the hashes the fragment pins**, on a fake data
root built from the committed receipts?

Zero model, GPU, network, tool and embedding contacts. The only large file
this module ever touches is the real ``facet-vectors.jsonl`` under
``SPEECHRL_DATA_DIR``, and only to hash it; the test skips when it is absent.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.base import (
    AGENT_CONTROLLERS,
    EVIDENCE_SOURCES,
    KNOWLEDGE_FUSERS,
    KNOWLEDGE_PROVIDERS,
    KNOWLEDGE_RANKERS,
    POLICIES,
    RESPONSE_FORMATS,
    SCORERS,
    CoreError,
)
from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.rails import controllers as rc
from speech_aware_evidence_acquisition.rails import phase_supply as ps

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXPERIMENT = "slurp-consumption-ku-s1-v2"
_PLACEHOLDER = "f" * 64

_VECTOR_RECEIPTS = (
    _REPO_ROOT
    / "docs"
    / "checks"
    / "speech-aware-evidence-acquisition"
    / "2026-09-06-slurp-ku-s1-vectors"
)


def _experiment() -> dict:
    path = _REPO_ROOT / "configs" / "experiment" / f"{_EXPERIMENT}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _composed():
    (cell,) = _experiment()["cells"]
    return compose(
        _REPO_ROOT,
        model=cell["model_fragment"],
        dataset=cell["dataset_fragment"],
        baseline=cell["baseline_fragment"],
        experiment=_EXPERIMENT,
    )


def _receipt(name: str) -> dict:
    return json.loads((_VECTOR_RECEIPTS / f"{name}.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. every id resolves in a core.base registry
# ---------------------------------------------------------------------------


def test_the_cell_composes_from_the_four_fragments_without_a_key_collision():
    composed = _composed()
    assert composed.values["experiment_id"] == "SAEA-SLURP-KU-S1-BLEND-CL-DEV1000-V1"
    assert composed.values["policy"] == "phase-direct-evidence-alpha-blend-v1"
    assert (
        composed.values["execution_plan"]["execution_profile"]
        == "bounded-discovery-probe"
    )
    # The config hash is what pins this cell's identity, the declared query
    # signal modality included. It is not asserted against a literal here --
    # MF-7 will change the query source and the hash with it, by design.
    assert len(composed.config_hash) == 64


def test_every_component_id_resolves_in_a_core_base_registry():
    """The 2026-09-03 owner rule, through the real registries. Mirrors the
    key -> registry map ``scripts/checks/engineering_base_check.py`` reads
    (``TOP_LEVEL_STRING_KEYS`` / ``TOP_LEVEL_LIST_KEY`` / ``NESTED_ID_KEYS``)."""

    values = _composed().values

    # `policy` resolves in POLICIES for a one-contact arm and in
    # AGENT_CONTROLLERS for a phase-program id; this cell is the latter.
    rc.register_phase_programs_v1()
    assert values["policy"] in set(AGENT_CONTROLLERS.names()) | set(POLICIES.names())
    AGENT_CONTROLLERS.resolve(values["policy"])

    EVIDENCE_SOURCES.resolve(values["evidence_source"])
    for name in values["scorers"]:
        SCORERS.resolve(name)

    for phase, entry in values["phase_material"].items():
        response_format_id = entry.get("response_format_id")
        if response_format_id is not None:
            RESPONSE_FORMATS.resolve(response_format_id)
        assert entry["predecessor_binding"] == "none", phase

    for phase, entry in values["phase_supply"].items():
        KNOWLEDGE_PROVIDERS.resolve(entry["provider"])
        KNOWLEDGE_RANKERS.resolve(entry["rank_policy"])
        KNOWLEDGE_FUSERS.resolve(entry["fuse_policy"])
        assert phase in rc.default_phase_program(values["policy"]).phase_names()


def test_an_unregistered_component_id_would_be_refused_by_the_seam():
    """The registry check is not decorative: the same loader refuses a
    provider id that resolves nowhere."""

    values = json.loads(json.dumps(dict(_composed().values)))
    values["phase_supply"]["evidence"]["provider"] = "kb-facet-v99"
    with pytest.raises(ps.PhaseSupplyError, match="KNOWLEDGE_PROVIDERS"):
        ps.load_phase_supply_specs(
            values, rc.default_phase_program(values["policy"])
        )
    with pytest.raises(CoreError):
        KNOWLEDGE_PROVIDERS.resolve("kb-facet-v99")


def test_the_spec_the_cell_loads_carries_the_lock_knobs():
    values = _composed().values
    specs = ps.load_phase_supply_specs(values, rc.default_phase_program(values["policy"]))
    spec = specs["evidence"]
    assert (spec.k, spec.tau, spec.alpha) == (5, 0.65, 0.45)
    assert spec.rank_weights == {"w_cos": 0.5, "w_prior": 0.3, "w_agree": 0.2}
    assert spec.fuse_coverage == {"m": 5, "c": 2, "top_l": 3}
    assert spec.dimensions == ("content",)
    assert spec.expose_facets is False


# ---------------------------------------------------------------------------
# 2. roster, budget and comparator, fixed before the query embedder is chosen
# ---------------------------------------------------------------------------


def test_the_roster_and_split_identity_are_ku_s1c_s_exactly():
    experiment = _experiment()
    sibling = json.loads(
        (
            _REPO_ROOT / "configs" / "experiment" / "slurp-consumption-ku-s1c-v1.json"
        ).read_text(encoding="utf-8")
    )
    assert experiment["split_id"] == sibling["split_id"] == "DEV-1000"
    assert (
        experiment["execution_plan"]["split_role"]
        == sibling["execution_plan"]["split_role"]
        == "dev"
    )
    identity = "8580d199bffc95a51ad6d8c5b2a2e9e39faa2c551dd095f8afcd78174a1e3c84"
    assert identity in experiment["population"]
    assert identity in sibling["population"]
    (cell,) = experiment["cells"]
    (sibling_cell,) = sibling["cells"]
    for key in ("arm", "model_fragment", "dataset_fragment"):
        assert cell[key] == sibling_cell[key]


def test_the_registered_budget_is_the_worst_case_two_contacts_per_row():
    plan = _experiment()["execution_plan"]
    assert plan["planned_model_calls"] == 2100
    assert plan["planned_speech_audio_seconds"] == 6000
    assert plan["planned_gpu_hours"] == 1.0
    basis = _experiment()["budget_basis"]
    assert "2,000 registered contacts plus 8 canaries" in basis
    assert "5,769.5874" in basis


def test_realized_contacts_are_declared_data_dependent_with_the_lock_s_numbers():
    text = _experiment()["realized_contacts"]
    assert "retain_prior" in text or "retain-primary" in text
    for number in ("660", "340", "674", "326"):
        assert number in text
    assert "expectation" in text.lower()


def test_the_decision_rule_is_v1_s_unchanged():
    rule = _experiment()["decision_rule"]
    assert "UNCHANGED" in rule
    assert "NEW500" in rule
    assert "net of KU-S1c" in rule
    assert "10,000" in rule and "20260903" in rule and "CI90" in rule


# ---------------------------------------------------------------------------
# 3. the preflight and the pinned hashes
# ---------------------------------------------------------------------------


def test_the_facet_pin_is_the_conversion_receipt_s_own_measured_hash():
    values = _composed().values
    source = values["phase_supply"]["evidence"]["facet_source"]
    receipt = _receipt("facet-vectors")
    assert source["sha256"] == receipt["output"]["sha256"] != _PLACEHOLDER
    assert source["relpath"] == receipt["output"]["artifact_relpath"]
    assert receipt["output"]["rows"] == 11514
    assert receipt["output"]["dims"] == 1024
    assert receipt["accounting"]["embedding_tool_contacts"] == 0
    assert receipt["accounting"]["frozen_core_contacts"] == 0


def test_the_query_pin_is_still_a_placeholder_and_says_why():
    """Owner rule 2026-09-06: the query must carry speech, and the only query
    vectors that exist embed response TEXT. The cell stays un-flyable, on
    purpose, and the fragment names what has to happen."""

    values = _composed().values
    source = values["phase_supply"]["evidence"]["query_source"]
    assert source["sha256"] == _PLACEHOLDER
    note = values["before_this_flies"]
    assert "speech-containing embedder chosen by MF-7" in note
    assert "owner rule 2026-09-06" in note
    for candidate in ("GLAP", "LCO-Embedding-Omni", "Omni-Embed-Nemotron"):
        assert candidate in note
    # And it declares a modality in the fixed vocabulary, so the seam accepts
    # the fragment's SHAPE while the hash still refuses its CONTENT.
    assert (
        ps.query_signal_modality(source, field="query_source")
        in ps.QUERY_SIGNAL_MODALITIES
    )
    # The text-only pass that did run keeps its own path, cited here.
    query_receipt = _receipt("query-vectors")
    assert query_receipt["embedded_signal_modality"] == "text-only"
    assert query_receipt["output"]["sha256"][:8] in note


def _write_vectors(path: Path, rows) -> str:
    text = "".join(
        json.dumps({"id": entry_id, "vectors": vectors}, sort_keys=True) + "\n"
        for entry_id, vectors in rows
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_the_preflight_accepts_a_correct_pin_and_refuses_a_wrong_one(tmp_path):
    """The mechanism the fragment's hashes ride, on a fake data root: a file
    that hashes to the pin loads, and one byte's difference refuses -- which
    is exactly why the query pin can be left as a placeholder without any
    risk of an accidental flight."""

    values = _composed().values
    spec_source = values["phase_supply"]["evidence"]["facet_source"]
    relpath = spec_source["relpath"]
    digest = _write_vectors(
        tmp_path / relpath,
        [
            ("facet:content:1", {"content": [1.0, 0.0]}),
            ("facet:content:2", {"content": [0.0, 1.0]}),
        ],
    )
    table = ps.load_sealed_vectors(
        tmp_path / relpath, expected_sha256=digest, dimensions=("content",)
    )
    assert set(table) == {"facet:content:1", "facet:content:2"}

    with pytest.raises(ps.PhaseSupplyError, match="hashes to"):
        ps.load_sealed_vectors(
            tmp_path / relpath,
            expected_sha256=spec_source["sha256"],
            dimensions=("content",),
        )
    with pytest.raises(ps.PhaseSupplyError, match="hashes to"):
        ps.load_sealed_vectors(
            tmp_path / relpath,
            expected_sha256=_PLACEHOLDER,
            dimensions=("content",),
        )


def test_the_real_facet_file_hashes_to_the_fragment_s_pin():
    """The strongest form of the same check, when the data root is present:
    the actual bytes the flight would load hash to the pinned value. Hashed,
    never parsed -- the file is 262 MB."""

    data_root = os.environ.get("SPEECHRL_DATA_DIR")
    if not data_root:
        pytest.skip("SPEECHRL_DATA_DIR is not set")
    source = _composed().values["phase_supply"]["evidence"]["facet_source"]
    path = Path(data_root) / source["relpath"]
    if not path.is_file():
        pytest.skip(f"{path} is not present on this host")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    assert digest.hexdigest() == source["sha256"]
    receipt = _receipt("facet-vectors")
    assert path.stat().st_size == receipt["output"]["bytes"]
