"""Owner decision 107: the two committed configs of the DEVEL-REMAINDER speech-query
preparation, and the generic runbooks that drive them.

Covered here (companion to ``test_slurp_devel_remainder_roster.py``, which
covers the roster and the runtime view, and to
``test_devel_remainder_preprocess_rosters.py``, which covers the packet pass):

* ``configs/preparation/slurp-devel-remainder-speech-query-encoding-protocol-v1.json``
  -- the ``saea-speech-query-encoding-protocol-v1`` the step-2b encoder run
  binds, checked through the runtime's OWN loaders
  (``core.speech_preparation_runtime.pinned_json`` / ``confined``,
  ``core.preparation_speech_queries.segment_plan``,
  ``contracts.ExecutionPlan``) rather than against a re-implementation;
* ``configs/preparation/slurp-devel-remainder-query-alias-v1.json`` -- the
  step-2c dimension-alias TEMPLATE, exercised end to end against
  ``core.preparation_vectors.prepare_vector_dimension_alias`` once materialised;
  and
* ``scripts/flights/batch/prep_generic_steps.py`` plus the two generic task
  entries.

ZERO model, encoder, tokenizer, scorer, GPU and network contacts, and no audio
sample, gold label, transcript or score is read. ``verify_encoder`` is the one
step of ``run_preparation`` deliberately NOT reproduced here: it re-hashes the
whole frozen Omni-Embed-Nemotron directory, which belongs to the run itself.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
_SRC = str(REPO / "src")
_existing_pythonpath = os.environ.get("PYTHONPATH", "")
if _SRC not in _existing_pythonpath.split(":"):
    os.environ["PYTHONPATH"] = _SRC + (":" + _existing_pythonpath if _existing_pythonpath else "")
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from speech_aware_evidence_acquisition.contracts import ExecutionPlan  # noqa: E402
from speech_aware_evidence_acquisition.core import (  # noqa: E402
    speech_preparation_runtime as runtime,
)
from speech_aware_evidence_acquisition.core.preparation_speech_queries import (  # noqa: E402
    segment_plan,
)
from speech_aware_evidence_acquisition.core.preparation_vectors import (  # noqa: E402
    prepare_vector_dimension_alias,
)

RUN = "SAEA-SLURP-DEVEL-REMAINDER-SPEECH-QUERY-ENCODING-V1"
EXPORT_ROW = "SAEA-SLURP-DEVEL-REMAINDER-QUERY-VECTOR-EXPORT-V1"
PROTOCOL_RELPATH = (
    "configs/preparation/slurp-devel-remainder-speech-query-encoding-protocol-v2.json"
)
ALIAS_RELPATH = "configs/preparation/slurp-devel-remainder-query-alias-v2.json"
PRECEDENT_PROTOCOL_RELPATH = (
    "configs/preparation/slurp-dev2000-added-speech-query-encoding-protocol-v1.json"
)
DATASET_RELPATH = "configs/dataset/slurp-speech-native-devel-remainder-v2.json"
ROSTER_RELPATH = "docs/receipts/rosters/slurp-devel-remainder-v2.json"
INVENTORY_RELPATH = "coordination/slurp-devel-remainder-speech-query-source-inventory-v2.json"
INVENTORY_SHA256 = "d8ca6915864d4b08f99157d990b52543f6b705184686546a5922acea6dda9aae"
SPLIT_IDENTITY = "f8af142bec49755d70364b665b31e3963972084fb73a568c9921f53b41fd341a"
ROSTER_ROWS = 6570
PLANNED_SPEECH_SECONDS = 18612
#: The superseded v1 pair stays committed and must stay unbound by the runbook.
PARENT_PROTOCOL_RELPATH = (
    "configs/preparation/slurp-devel-remainder-speech-query-encoding-protocol-v1.json"
)
PARENT_ALIAS_RELPATH = "configs/preparation/slurp-devel-remainder-query-alias-v1.json"


def _load(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


steps = _load("prep_generic_steps", "scripts/flights/batch/prep_generic_steps.py")
PREPARATION = steps.PREPARATION_SETS["devel-remainder"]


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(relpath: str):
    return json.loads((REPO / relpath).read_text(encoding="utf-8"))


PROTOCOL = load_json(PROTOCOL_RELPATH)
ALIAS_TEMPLATE = load_json(ALIAS_RELPATH)
PROTOCOL_SHA256 = raw_sha256(REPO / PROTOCOL_RELPATH)


def _data_root() -> Path | None:
    raw = os.environ.get("SPEECHRL_DATA_DIR", "").strip()
    root = Path(raw) if raw else None
    return root if root is not None and root.is_dir() else None


requires_data_root = pytest.mark.skipif(
    _data_root() is None, reason="SPEECHRL_DATA_DIR is not materialised on this host"
)


# ---------------------------------------------------------------------------
# The step-2b encoding protocol.
# ---------------------------------------------------------------------------


def test_protocol_carries_the_registered_recipe_constants() -> None:
    assert PROTOCOL["schema"] == "saea-speech-query-encoding-protocol-v1"
    assert PROTOCOL["expected_unique_spans"] == ROSTER_ROWS
    assert PROTOCOL["query_prompt"] == "query: "
    assert PROTOCOL["dimension"] == 2048
    assert PROTOCOL["cpu_workers"] == 8  # decision 107: prepared fast, with more workers
    assert PROTOCOL["monitor_interval_seconds"] == 10
    assert PROTOCOL["max_seconds"] == 120.0
    assert PROTOCOL["overlap_seconds"] == 8.0
    assert PROTOCOL["boundary_policy"] == "fixed-stride-complete-final-tail-v1"


def test_protocol_recipe_matches_the_dev2000_added_precedent_field_for_field() -> None:
    """Only the roster-bound fields and cpu_workers may differ from the precedent."""

    precedent = load_json(PRECEDENT_PROTOCOL_RELPATH)
    assert set(PROTOCOL) == set(precedent)
    roster_bound = {
        "cache_relpath",
        "expected_unique_spans",
        "isolation",
        "output_relpath",
        "query_rows_relpath",
        "roster_sha256",
        "sources",
    }
    for key in set(PROTOCOL) - roster_bound - {"cpu_workers"}:
        assert PROTOCOL[key] == precedent[key], key
    for key in roster_bound:
        assert PROTOCOL[key] != precedent[key], key
    assert precedent["cpu_workers"] == 4
    assert PROTOCOL["cpu_workers"] == 8
    assert PROTOCOL["cpu_workers"] <= 8  # the standing CPU-worker cap beside a GPU campaign


def test_protocol_roster_hash_is_the_committed_roster_receipt() -> None:
    roster_sha256 = raw_sha256(REPO / ROSTER_RELPATH)
    assert PROTOCOL["roster_sha256"] == roster_sha256
    assert PROTOCOL["sources"]["derived_from"]["roster_receipt"] == {
        "path": ROSTER_RELPATH,
        "sha256": roster_sha256,
    }
    receipt = load_json(ROSTER_RELPATH)
    assert receipt["roster_id"] == "SLURP-DEVEL-REMAINDER-V2"
    assert len(receipt["items"]) == PROTOCOL["expected_unique_spans"]
    assert receipt["carved_out_reserved_sets"]["union_recordings"] == 120


def test_the_superseded_v1_preparation_configs_are_committed_and_bound_by_nothing() -> None:
    """V1 stays on disk as the parent; the runbook must name only V2."""

    parent_protocol = load_json(PARENT_PROTOCOL_RELPATH)
    parent_alias = load_json(PARENT_ALIAS_RELPATH)
    assert parent_protocol["expected_unique_spans"] == 6690
    assert parent_alias["expected_rows"] == 6690
    bound = {
        PREPARATION.protocol_relpath,
        PREPARATION.alias_template_relpath,
        PREPARATION.roster_relpath,
        PREPARATION.dataset_relpath,
        PREPARATION.inventory_relpath,
    }
    assert PARENT_PROTOCOL_RELPATH not in bound
    assert PARENT_ALIAS_RELPATH not in bound
    assert "docs/receipts/rosters/slurp-devel-remainder-v1.json" not in bound
    assert "configs/dataset/slurp-speech-native-devel-remainder.json" not in bound


def test_protocol_runtime_view_pin_is_the_committed_dataset_fragment() -> None:
    view = load_json(DATASET_RELPATH)
    pinned = PROTOCOL["sources"]["derived_from"]["runtime_view"]
    assert pinned["path"] == DATASET_RELPATH
    assert pinned["raw_sha256"] == raw_sha256(REPO / DATASET_RELPATH)
    assert pinned["canonical_runtime_view_sha256"] == view["runtime_view_sha256"]
    assert view["split_identity_hash"] == SPLIT_IDENTITY
    assert view["count"] == ROSTER_ROWS


def test_protocol_sources_pin_the_step_2a_inventory_not_the_runtime_view() -> None:
    """The DEV-2000-ADDED registration needed two corrections for exactly this."""

    sources = PROTOCOL["sources"]
    assert sources["schema"] == "saea-speech-query-source-inventory-v1"
    assert sources["sha256"] == INVENTORY_SHA256
    assert sources["path"].endswith("/" + INVENTORY_RELPATH)
    assert sources["path"].startswith("${SAEA_DATA_ROOT}/")  # data-root placeholder (owner rulings 289 B / 290 B)


def test_protocol_artifact_paths_are_confined_and_name_this_roster(tmp_path: Path) -> None:
    keys = ("output_relpath", "query_rows_relpath", "cache_relpath")
    resolved = {key: runtime.confined(tmp_path, PROTOCOL[key]) for key in keys}
    assert len(set(resolved.values())) == len(keys)
    assert PROTOCOL["output_relpath"] == "prepared/%s/index.json" % RUN
    assert PROTOCOL["query_rows_relpath"] == "prepared/%s/queries.jsonl" % RUN
    assert PROTOCOL["cache_relpath"] == "prepared/slurp-devel-remainder-speech-query-span-cache-v1"
    for path in resolved.values():
        assert path.is_relative_to(tmp_path.resolve())


PROSE_KEYS = frozenset(
    {"answer_authority", "built_by", "contact_policy", "how_to_fill", "isolation",
     "registration_note"}
)


def _binding_values(node):
    """Every non-prose leaf: the paths, relpaths, hashes and counts that bind."""

    if isinstance(node, dict):
        for key, value in node.items():
            if key not in PROSE_KEYS:
                yield from _binding_values(value)
    elif isinstance(node, list):
        for item in node:
            yield from _binding_values(item)
    else:
        yield node


def test_no_other_roster_name_leaks_into_a_binding_field() -> None:
    """Prose may cite the DEV-2000-ADDED precedent; no binding may name it."""

    for label, document in ((PROTOCOL_RELPATH, PROTOCOL), (ALIAS_RELPATH, ALIAS_TEMPLATE)):
        text = " ".join(str(value) for value in _binding_values(document))
        for foreign in ("DEV2000", "DEV-2000", "dev2000", "FOLD-A", "fold-a", "DEV-1000",
                        "stage3-construction-r01"):
            assert foreign not in text, (label, foreign)
        assert "devel-remainder" in text.lower()


def test_the_step_2b_execution_plan_validates_and_binds_the_committed_protocol() -> None:
    plan = ExecutionPlan(
        attempt_id="encode-v1",
        carrier_lock_key="slurp",
        execution_profile="bounded-discovery-probe",
        planned_gpu_hours=2.0,
        planned_model_calls=ROSTER_ROWS,
        planned_speech_audio_seconds=PLANNED_SPEECH_SECONDS,
        protocol_hash=PROTOCOL_SHA256,
        run_id=RUN,
        split_identity_hash=SPLIT_IDENTITY,
        split_role="dev",
    ).validate()
    assert plan.schema == "saea-execution-plan-v1"
    assert plan.protocol_hash == PROTOCOL_SHA256
    assert plan.planned_model_calls == PROTOCOL["expected_unique_spans"]


# ---------------------------------------------------------------------------
# The generic preparation set and its minted runtime config.
# ---------------------------------------------------------------------------


def test_the_preparation_set_agrees_with_every_committed_artifact() -> None:
    assert PREPARATION.run_id == RUN
    assert PREPARATION.export_row == EXPORT_ROW
    assert PREPARATION.protocol_relpath == PROTOCOL_RELPATH
    assert PREPARATION.alias_template_relpath == ALIAS_RELPATH
    assert PREPARATION.roster_relpath == ROSTER_RELPATH
    assert PREPARATION.dataset_relpath == DATASET_RELPATH
    assert PREPARATION.inventory_relpath == INVENTORY_RELPATH
    assert PREPARATION.inventory_sha256 == INVENTORY_SHA256 == PROTOCOL["sources"]["sha256"]
    assert PREPARATION.rows == ROSTER_ROWS == PROTOCOL["expected_unique_spans"]
    assert PREPARATION.vector_width == PROTOCOL["dimension"]
    assert PREPARATION.split_identity_hash == SPLIT_IDENTITY
    assert PREPARATION.split_role == "dev"
    assert PREPARATION.planned_speech_audio_seconds == PLANNED_SPEECH_SECONDS
    assert PREPARATION.queries_relpath == PROTOCOL["query_rows_relpath"]
    assert PREPARATION.encode_receipt_relpath == ALIAS_TEMPLATE["source_receipts"][0]["relpath"]
    assert PREPARATION.alias_receipt_relpath == ALIAS_TEMPLATE["receipt_relpath"]
    assert PREPARATION.segments_relpath == ALIAS_TEMPLATE["output_relpath"]
    assert PREPARATION.content_relpath.endswith("/query-vectors-speech-content-v1.jsonl")


def test_the_minted_runtime_config_validates_and_binds_the_committed_protocol() -> None:
    """The generator's document is exactly what ``run_preparation`` consumes."""

    document = steps.build_runtime_config(
        PREPARATION,
        study_head="0" * 40,
        protocol_sha256=PROTOCOL_SHA256,
        umbrella_lock="/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json",
        umbrella_lock_sha256="c" * 64,
    )
    assert set(document) == {"plan", "protocol", "session_id", "study_head", "umbrella_lock"}
    plan = ExecutionPlan(**document["plan"]).validate()
    assert plan.run_id == RUN
    assert plan.attempt_id == "encode-v1"
    assert plan.split_role == "dev"
    assert plan.split_identity_hash == SPLIT_IDENTITY
    assert plan.execution_profile == "bounded-discovery-probe"
    assert plan.planned_model_calls == ROSTER_ROWS
    assert plan.planned_speech_audio_seconds == PLANNED_SPEECH_SECONDS
    # run_preparation refuses any plan whose protocol_hash differs from the
    # pinned protocol binding, so both must name the same committed bytes.
    assert plan.protocol_hash == document["protocol"]["sha256"] == PROTOCOL_SHA256
    assert document["protocol"]["path"] == PROTOCOL_RELPATH
    assert PREPARATION.runtime_config_relpath == (
        "coordination/slurp-devel-remainder-query-encoding-v1/runtime-config-v1.json"
    )


def test_an_unknown_preparation_set_is_refused() -> None:
    with pytest.raises(steps.PreparationRunbookError):
        steps.resolve_set("no-such-set")


# ---------------------------------------------------------------------------
# The step-2c dimension-alias template.
# ---------------------------------------------------------------------------


def test_alias_template_is_the_contract_field_set_plus_the_how_to_fill_note() -> None:
    assert set(ALIAS_TEMPLATE) == steps.ALIAS_CONFIG_FIELDS | {"how_to_fill"}
    assert isinstance(ALIAS_TEMPLATE["how_to_fill"], str)
    assert "PENDING_STEP_2B_QUERIES_SHA256" in ALIAS_TEMPLATE["how_to_fill"]
    assert "PENDING_STEP_2B_RECEIPT_SHA256" in ALIAS_TEMPLATE["how_to_fill"]


def test_alias_template_pending_markers_sit_exactly_where_step_2b_output_lands() -> None:
    assert ALIAS_TEMPLATE["source"]["sha256"] == "PENDING_STEP_2B_QUERIES_SHA256"
    assert ALIAS_TEMPLATE["source_receipts"][0]["sha256"] == "PENDING_STEP_2B_RECEIPT_SHA256"
    text = json.dumps(ALIAS_TEMPLATE)
    assert text.count("PENDING_STEP_2B_QUERIES_SHA256") == 2  # the field and the note
    assert text.count("PENDING_STEP_2B_RECEIPT_SHA256") == 2


def test_alias_template_cross_references_the_protocol_and_the_committed_receipts() -> None:
    assert ALIAS_TEMPLATE["schema"] == "saea-sealed-segment-vector-dimension-alias-v1"
    assert ALIAS_TEMPLATE["expected_rows"] == PROTOCOL["expected_unique_spans"]
    assert ALIAS_TEMPLATE["vector_width"] == PROTOCOL["dimension"]
    assert ALIAS_TEMPLATE["source"]["relpath"] == PROTOCOL["query_rows_relpath"]
    assert ALIAS_TEMPLATE["source"]["kind"] == "sealed-segment-vectors"
    assert ALIAS_TEMPLATE["source"]["dimension"] == "content"
    assert ALIAS_TEMPLATE["target_dimension"] == "intent-boundary"
    assert ALIAS_TEMPLATE["output_relpath"] == (
        "vectors/slurp-devel-remainder-v1/query-vectors-speech-segments.jsonl"
    )
    assert ALIAS_TEMPLATE["receipt_relpath"] == (
        "prepared/SAEA-SLURP-DEVEL-REMAINDER-ALIAS-V1/query-dimension-alias.json"
    )
    receipts = ALIAS_TEMPLATE["source_receipts"]
    assert receipts[0]["relpath"] == "preparation-runs/%s/encode-v1/receipt.json" % RUN
    assert receipts[0]["root"] == "data"
    assert receipts[1] == {
        "relpath": DATASET_RELPATH,
        "root": "repository",
        "sha256": raw_sha256(REPO / DATASET_RELPATH),
    }
    assert receipts[2] == {
        "relpath": ROSTER_RELPATH,
        "root": "repository",
        "sha256": raw_sha256(REPO / ROSTER_RELPATH),
    }


def test_materialising_the_template_yields_exactly_the_contract_field_set() -> None:
    config = steps.materialise_alias_config(
        ALIAS_TEMPLATE, queries_sha256="a" * 64, receipt_sha256="b" * 64
    )
    assert set(config) == steps.ALIAS_CONFIG_FIELDS
    assert config["source"]["sha256"] == "a" * 64
    assert config["source_receipts"][0]["sha256"] == "b" * 64
    assert "PENDING_" not in json.dumps(config)
    # The template itself is never mutated: the committed bytes stay a template.
    assert ALIAS_TEMPLATE["source"]["sha256"] == "PENDING_STEP_2B_QUERIES_SHA256"


def test_the_unmaterialised_template_is_refused_by_the_alias_contract(tmp_path: Path) -> None:
    with pytest.raises(Exception) as error:
        prepare_vector_dimension_alias(
            dict(ALIAS_TEMPLATE), repo_root=REPO, data_root=tmp_path
        )
    assert "wrong fields" in str(error.value)


def _write_segment_source(data_root: Path, relpath: str, width: int, rows: int) -> str:
    path = data_root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for index in range(rows):
        vector = [float(index + position) for position in range(width)]
        lines.append(
            json.dumps(
                {
                    "id": "slurp:devel:%06d:audio-%d" % (index, index),
                    "audio_sha256": "%064x" % (index + 1),
                    "source_frames": 16000,
                    "source_sample_rate_hz": 16000,
                    "segments": [
                        {
                            "id": "slurp:devel:%06d:audio-%d#0" % (index, index),
                            "start_frame": 0,
                            "end_frame": 16000,
                            "vectors": {"content": vector},
                        }
                    ],
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    raw = ("\n".join(lines) + "\n").encode("utf-8")
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def test_the_materialised_config_runs_through_the_real_alias_contract(tmp_path: Path) -> None:
    """End to end on a synthetic data root: the committed shape is runnable.

    ``expected_rows`` and ``vector_width`` are scaled down so the synthetic
    source stays small; every other field is the committed one, including both
    confined relpaths and all three source-receipt pins.
    """

    rows, width = 2, 4
    queries_sha256 = _write_segment_source(
        tmp_path, ALIAS_TEMPLATE["source"]["relpath"], width, rows
    )
    receipt_relpath = ALIAS_TEMPLATE["source_receipts"][0]["relpath"]
    receipt_path = tmp_path / receipt_relpath
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_bytes(b'{"status": "SEALED"}\n')
    config = steps.materialise_alias_config(
        ALIAS_TEMPLATE,
        queries_sha256=queries_sha256,
        receipt_sha256=raw_sha256(receipt_path),
    )
    config["expected_rows"], config["vector_width"] = rows, width

    result = prepare_vector_dimension_alias(config, repo_root=REPO, data_root=tmp_path)

    output = result["output"]
    assert output["row_count"] == rows
    assert output["segment_count"] == rows
    assert output["source_dimension"] == "content"
    assert output["target_dimension"] == "intent-boundary"
    assert output["values_unchanged"] is True
    assert output["max_absolute_delta"] == 0.0
    assert output["encoder_contacts"] == output["tokenizer_contacts"] == 0
    assert output["model_contacts"] == 0
    exported = tmp_path / ALIAS_TEMPLATE["output_relpath"]
    assert raw_sha256(exported) == output["output_sha256"]
    first = json.loads(exported.read_text(encoding="utf-8").splitlines()[0])
    assert set(first["segments"][0]["vectors"]) == {"intent-boundary"}
    assert (tmp_path / ALIAS_TEMPLATE["receipt_relpath"]).is_file()


def test_materialise_refuses_a_receipt_that_is_not_the_sealed_step_2b_one() -> None:
    with pytest.raises(steps.PreparationRunbookError):
        steps.require({"status": "ABORTED"}, "status", "SEALED", "step-2b receipt")


# ---------------------------------------------------------------------------
# The two generic runbooks.
# ---------------------------------------------------------------------------


def _executable_lines(relpath: str) -> str:
    """A shell script without its comment lines: what it actually runs.

    The generic runbooks NAME the sealed R01 pair in their headers as the
    precedent they generalise; what must not happen is INVOKING one.
    """

    text = (REPO / relpath).read_text("utf-8")
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )


def test_the_packet_task_entry_keeps_the_dirty_tree_refusal_and_the_watchdog() -> None:
    script = (REPO / "scripts/flights/batch/prep_generic_task_entry.sh").read_text("utf-8")
    assert "dirty tree; refusing" in script
    assert "PREP_ROSTER" in script and "PREP_WORKERS" in script
    assert "PREP_PROMOTE_WORKERS" in script and "PREP_SIDECAR_FRAGMENT" in script
    assert "watchdog" in script and "PREP_MEMORY_FLOOR_GB:-6" in script
    assert "--preflight-only" in script and "--run" in script
    assert "prep_generic_steps.py roster-facts" in script
    # It never runs an encoder preparation or invokes an R01 script.
    assert "speech_preparation_runtime" not in script
    assert "r01_" not in _executable_lines("scripts/flights/batch/prep_generic_task_entry.sh")


def test_the_encode_task_entry_drives_the_committed_template_and_helpers() -> None:
    script = (REPO / "scripts/flights/batch/prep_generic_encode_task_entry.sh").read_text("utf-8")
    assert "dirty tree; refusing" in script
    assert "a GPU flight is running; refusing" in script
    assert "prep_generic_steps.py" in script or "$STEPS" in script
    assert "speech_aware_evidence_acquisition.core.preparation_vectors" in script
    assert "scripts/build_slurp_query_content_derivative.py" in script
    assert "speech_preparation_runtime" in script  # step 2b is its own launch
    assert "r01_" not in _executable_lines(
        "scripts/flights/batch/prep_generic_encode_task_entry.sh"
    )


def test_the_r01_runbooks_are_untouched_by_this_registration() -> None:
    """The generic runbooks are siblings, never edits of the sealed R01 pair."""

    for relpath in (
        "scripts/flights/batch/r01_prep23.sh",
        "scripts/flights/batch/r01_prep23_steps.py",
        "scripts/flights/batch/prep_r01_task_entry.sh",
        "scripts/flights/batch/prep_r01_encode_task_entry.sh",
    ):
        text = (REPO / relpath).read_text("utf-8")
        assert "devel-remainder" not in text, relpath
        assert "prep_generic" not in text, relpath


# ---------------------------------------------------------------------------
# Against the materialised data root.
# ---------------------------------------------------------------------------


@requires_data_root
def test_protocol_bindings_load_through_the_runtime_loaders() -> None:
    """Every pinned binding of the protocol resolves and hashes as registered."""

    data_root = _data_root()
    assert data_root is not None
    previous = Path.cwd()
    os.chdir(REPO)
    try:
        protocol = runtime.pinned_json({"path": PROTOCOL_RELPATH, "sha256": PROTOCOL_SHA256})
        sources = runtime.pinned_json(protocol["sources"])
        encoder = runtime.pinned_json(protocol["encoder"])
    finally:
        os.chdir(previous)
    assert sources["roster_sha256"] == protocol["roster_sha256"]
    assert sources["schema"] == "saea-speech-query-source-inventory-v1"
    assert sources["count"] == ROSTER_ROWS
    assert sources["split_identity_hash"] == SPLIT_IDENTITY
    assert encoder["schema"] == "saea-pinned-speech-query-encoder-inventory-v1"


@requires_data_root
def test_the_inventory_reproduces_the_expected_span_count_and_audio_budget() -> None:
    """The exact arithmetic ``run_preparation`` runs before the first contact."""

    data_root = _data_root()
    assert data_root is not None
    sources = json.loads((data_root / INVENTORY_RELPATH).read_text(encoding="utf-8"))
    rows = sources["rows"]
    identity = hashlib.sha256(
        "\n".join(sorted("slurp/%s" % row["id"] for row in rows)).encode("utf-8")
    ).hexdigest()
    assert identity == SPLIT_IDENTITY
    spans = {
        (
            row["audio_sha256"],
            row["source_frames"],
            row["source_sample_rate_hz"],
            span["start_frame"],
            span["end_frame"],
        )
        for row in rows
        for span in segment_plan(
            row["source_frames"],
            row["source_sample_rate_hz"],
            max_seconds=PROTOCOL["max_seconds"],
            overlap_seconds=PROTOCOL["overlap_seconds"],
        )
    }
    audio_seconds = sum((end - start) / rate for _sha, _frames, rate, start, end in spans)
    assert len(spans) == PROTOCOL["expected_unique_spans"]
    assert len(spans) <= ROSTER_ROWS
    assert audio_seconds <= PLANNED_SPEECH_SECONDS
