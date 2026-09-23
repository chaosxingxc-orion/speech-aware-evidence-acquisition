"""Stage-3 S3-5: the curated authored-deltas document -> RELEASE SOURCE
conversion, and the whole release path it unblocks.

The gap this closes (S3-4s hand-off note): the E-release path of
``scripts/flights/batch/adv1_to_deltas.sh`` passed the curator's
``--out-authored`` document (schema ``saea-stage3-authored-deltas-v2``)
straight to ``core.semantic_knowledge_preparation.
prepare_semantic_knowledge_store``, which reads an ``authored_source``
only through the shared ``saea-authored-semantic-knowledge-source-v1``
envelope. The conversion did not exist, so no release could ever have run.

Everything below is SYNTHETIC and confined to ``tmp_path``: a fake
advantage-outputs file, a fake ``pairs.json``, fake rosters, a fake repo
root and a fake data root. No test here reads ``SPEECHRL_DATA_DIR``, the
real knowledge namespace, or any model, tokenizer, encoder, scorer, GPU or
network surface -- the whole S3-5 tail is pure file-to-file curation.

The end-to-end proof, for the generation store and for its derangement
twin:

    curate (+ wrap) -> materialise the release registration ->
    prepare_semantic_knowledge_store -> release / completion / snapshot ->
    load_knowledge_store_binding -> the four per-node ``context_supply``
    routes of ``rails.knowledge_stores`` actually serve the released
    snapshot.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.preparation import canonical_bytes
from speech_aware_evidence_acquisition.core.semantic_knowledge_preparation import (
    SemanticKnowledgePreparationError,
    prepare_semantic_knowledge_store,
)
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.rails import knowledge_build as _registrations  # noqa: F401
from speech_aware_evidence_acquisition.rails.controllers import PhaseProgram, PhaseSpec
from speech_aware_evidence_acquisition.rails.knowledge import (
    AgentStateArtifact,
    QueryState,
)
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    build_knowledge_store_supply,
    load_knowledge_store_binding,
)
from speech_aware_evidence_acquisition.rails.runner import AgentRuntimeContext
from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import (
    STAGE3_DELTA_V2_BUILD_POLICY_ID,
)
from speech_aware_evidence_acquisition.rails.stage3_delta_supply import (
    STAGE3_DELTA_CONTEXT_PROVIDER_ID,
    STAGE3_DELTA_UNCONDITIONAL_PROVIDER_ID,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relpath)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, module)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


curator = _load(
    "_wrap_test_delta_store", "scripts/build_slurp_stage3_delta_store.py"
)
source_cli = _load(
    "_wrap_test_delta_source", "scripts/build_slurp_stage3_delta_source.py"
)
twin_cli = _load("_wrap_test_delta_twin", "scripts/build_slurp_stage3_delta_twin.py")
steps = _load(
    "_wrap_test_adv1_steps", "scripts/flights/batch/adv1_to_deltas_steps.py"
)

SHA_B = "b" * 64
CONSTRUCTION_IDS = ("train-1", "train-2")
SCOPE_IDS = ("train-1", "train-2", "train-3")
INVENTORY = ("alarm_set", "alarm_query", "play_music", "music_query")
SPLIT = split_identity_hash(prefixed("slurp", CONSTRUCTION_IDS))
TWIN_SEED = 20260922

#: Two synthetic advantage contacts, three NODE-attributed blocks each, so
#: the released store carries solver, perception, reviewer and planner rows
#: -- one per route the delta cell declares. Statement texts are pairwise
#: far apart in token-Jaccard terms so nothing is deduped away.
RESPONSES = {
    "train-1": (
        "NODE: solver\n"
        "DELTA-KIND: slot-contract\n"
        "TARGET: alarm_set\n"
        "STATEMENT: Keep the time slot whenever a clock time is stated.\n"
        "NODE: perception\n"
        "DELTA-KIND: perception-hint\n"
        "TARGET: alarm_query\n"
        "STATEMENT: Propose a query reading when the utterance asks about an "
        "existing reminder.\n"
        "NODE: reviewer\n"
        "DELTA-KIND: reviewer-criterion\n"
        "TARGET: alarm_set\n"
        "STATEMENT: Reject a draft that invents a date nobody mentioned.\n"
    ),
    "train-2": (
        "NODE: solver\n"
        "DELTA-KIND: slot-contract\n"
        "TARGET: play_music\n"
        "STATEMENT: Carry the artist mention through verbatim, without "
        "expanding it.\n"
        "NODE: perception\n"
        "DELTA-KIND: perception-hint\n"
        "TARGET: music_query\n"
        "STATEMENT: Prefer a lookup reading over playback when nothing is "
        "requested to start.\n"
        "NODE: planner\n"
        "DELTA-KIND: planner-rule\n"
        "TARGET: play_music\n"
        "STATEMENT: Stop after one revisit; further loops add cost and no "
        "evidence.\n"
    ),
}


# ---------------------------------------------------------------------------
# Synthetic world
# ---------------------------------------------------------------------------


def _roster(ids, *, roster_id, roster_role="construction"):
    return {
        "schema": "saea-roster-receipt-v1",
        "roster_id": roster_id,
        "carrier_lock_key": "slurp",
        "split_role": "discovery",
        "roster_role": roster_role,
        "items": [{"sample_id": sample_id, "stratum": "synthetic"} for sample_id in ids],
        "split_identity_hash": split_identity_hash(prefixed("slurp", tuple(ids))),
    }


def _write_json(path: Path, document: object) -> str:
    raw = canonical_bytes(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _curation_inputs(tmp_path: Path) -> tuple[Path, Path]:
    pairs_path = tmp_path / "inputs" / "pairs.json"
    pairs_path.parent.mkdir(parents=True, exist_ok=True)
    pairs_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "sample_id": sample_id,
                        "best": {"sample_index": 2, "response_text_sha256": "a" * 64},
                        "worst": {"sample_index": 4, "response_text_sha256": "b" * 64},
                    }
                    for sample_id in CONSTRUCTION_IDS
                ]
            }
        ),
        encoding="utf-8",
        newline="\n",
    )
    outputs_path = tmp_path / "inputs" / "advantage-outputs.jsonl"
    outputs_path.write_text(
        "".join(
            json.dumps(
                {
                    "sample_id": sample_id,
                    "response_text": RESPONSES[sample_id],
                    "disagreement": 0.9 - 0.1 * index,
                }
            )
            + "\n"
            for index, sample_id in enumerate(CONSTRUCTION_IDS)
        ),
        encoding="utf-8",
        newline="\n",
    )
    return pairs_path, outputs_path


@pytest.fixture()
def world(tmp_path):
    """Curate the generation document and its wrapper, and derange the twin.

    Returns the synthetic repo root, data root and every path the release
    path needs. Nothing outside ``tmp_path`` is written or read.
    """

    repo_root, data_root = tmp_path / "repo", tmp_path / "data"
    prepared = data_root / "prepared" / "SAEA-SLURP-STAGE3-DELTAS-V1"
    prepared.mkdir(parents=True)
    (repo_root / "docs").mkdir(parents=True)
    pairs_path, outputs_path = _curation_inputs(tmp_path)

    authored = prepared / "authored-stage3-deltas-v1.json"
    source = prepared / "source-stage3-deltas-v1.json"
    assert (
        curator.main(
            [
                "--advantage-outputs", str(outputs_path),
                "--pairs", str(pairs_path),
                "--repo-root", str(repo_root),
                "--predecessor", "none",
                "--iteration", "1",
                "--run-id", "SAEA-TEST-ADVANTAGE-V1",
                "--out-authored", str(authored),
                "--out-source", str(source),
                # The legacy facet rule: this world's whole point is the
                # release PATH (curate -> wrap -> register -> release ->
                # route), and target-only keeps its rows' facets equal to
                # their TARGETs so the per-node route assertions below read
                # the same as they did before S3-5 revision v1r. The v1r
                # rule itself is proven in test_stage3_delta_store_v2.py.
                "--facet-rule", "target-only",
                "--source-split-identity-hash", SPLIT,
            ]
        )
        == 0
    )

    twin_authored = prepared / "authored-stage3-deltas-twin-v1.json"
    twin_source = prepared / "source-stage3-deltas-twin-v1.json"
    assert (
        twin_cli.main(
            ["--authored", str(authored), "--seed", str(TWIN_SEED),
             "--out", str(twin_authored)]
        )
        == 0
    )
    assert (
        source_cli.main(
            ["--authored", str(twin_authored), "--out", str(twin_source),
             "--source-split-identity-hash", SPLIT]
        )
        == 0
    )

    scope_sha = _write_json(prepared / "outer-construction-roster.json",
                            _roster(SCOPE_IDS, roster_id="synthetic-scope"))
    permitted_sha = _write_json(prepared / "permitted-roster.json",
                                _roster(CONSTRUCTION_IDS, roster_id="synthetic-permitted"))
    forbidden_relpath = "docs/receipts/rosters/synthetic-evaluation-v1.json"
    forbidden_sha = _write_json(
        repo_root / forbidden_relpath,
        _roster(("eval-1", "eval-2"), roster_id="synthetic-eval",
                roster_role="evaluation"),
    )
    return {
        "repo_root": repo_root,
        "data_root": data_root,
        "prepared": prepared,
        "authored": authored,
        "source": source,
        "twin_authored": twin_authored,
        "twin_source": twin_source,
        "pairs": pairs_path,
        "outputs": outputs_path,
        "scope_sha": scope_sha,
        "permitted_sha": permitted_sha,
        "forbidden_relpath": forbidden_relpath,
        "forbidden_sha": forbidden_sha,
    }


def _template(world, *, authored_relpath, namespace, registration_id):
    """A release-registration TEMPLATE in exactly the committed shape."""

    return {
        "schema": "saea-authored-semantic-knowledge-preparation-v1",
        "registration_id": registration_id,
        "template_note": "TEMPLATE, never passed to the preparer.",
        "carrier_lock_key": "slurp",
        "source_partition_role": "train",
        "source_split_identity_hash": "PENDING_S3_3_DISAGREEING_SPLIT_IDENTITY_HASH",
        "builder_policy_id": STAGE3_DELTA_V2_BUILD_POLICY_ID,
        "store_id": "stage3-deltas",
        "store_role": "stage3-deltas",
        "authored_source": {
            "root": "data",
            "relpath": authored_relpath,
            "sha256": "PENDING_S3_5_AUTHORED_SHA256",
        },
        "construction_scope": {
            "root": "data",
            "relpath": "prepared/SAEA-SLURP-STAGE3-DELTAS-V1/outer-construction-roster.json",
            "sha256": "PENDING_S3_5_CONSTRUCTION_SCOPE_SHA256",
        },
        "permitted_roster": {
            "root": "data",
            "relpath": "prepared/SAEA-SLURP-STAGE3-DELTAS-V1/permitted-roster.json",
            "sha256": "PENDING_S3_5_PERMITTED_ROSTER_SHA256",
        },
        "forbidden_rosters": [
            {
                "root": "repo",
                "relpath": world["forbidden_relpath"],
                "sha256": world["forbidden_sha"],
            }
        ],
        "output_namespace": namespace,
    }


def _run_registration(world, *, template, out_relpath):
    """Run the runbook's own registration step (``adv1_to_deltas_steps.py``)
    and return ``(exit_code, out_path)`` -- the CLI reports a refusal as a
    non-zero exit with a message on stderr, never as a raised exception."""

    template_relpath = f"docs/readiness/synthetic/{out_relpath}.template.json"
    (world["repo_root"] / template_relpath).parent.mkdir(parents=True, exist_ok=True)
    (world["repo_root"] / template_relpath).write_text(
        json.dumps(template, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    out_path = world["repo_root"] / "docs" / "readiness" / "synthetic" / f"{out_relpath}.json"
    return steps.main(
        [
            "--repo-root", str(world["repo_root"]),
            "--data-root", str(world["data_root"]),
            "registration",
            "--template", template_relpath,
            "--out", str(out_path),
            "--source-split-identity-hash", SPLIT,
        ]
    ), out_path


def _materialise(world, *, template, out_relpath):
    exit_code, out_path = _run_registration(
        world, template=template, out_relpath=out_relpath
    )
    assert exit_code == 0
    return out_path


def _release(world, *, authored_relpath, namespace, registration_id, out_relpath):
    registration_path = _materialise(
        world,
        template=_template(
            world, authored_relpath=authored_relpath, namespace=namespace,
            registration_id=registration_id,
        ),
        out_relpath=out_relpath,
    )
    return prepare_semantic_knowledge_store(
        registration_path,
        repo_root=world["repo_root"],
        data_root=world["data_root"],
    )


GENERATION = {
    "authored_relpath": "prepared/SAEA-SLURP-STAGE3-DELTAS-V1/source-stage3-deltas-v1.json",
    "namespace": "knowledge/slurp/semantic/stage3-deltas-v1",
    "registration_id": "SYNTHETIC-STAGE3-DELTAS-PREPARATION-V1",
    "out_relpath": "stage3-deltas-v1-release-registration",
}
TWIN = {
    "authored_relpath": "prepared/SAEA-SLURP-STAGE3-DELTAS-V1/source-stage3-deltas-twin-v1.json",
    "namespace": "knowledge/slurp/semantic/stage3-deltas-twin-v1",
    "registration_id": "SYNTHETIC-STAGE3-DELTAS-TWIN-PREPARATION-V1",
    "out_relpath": "stage3-deltas-twin-v1-release-registration",
}


# ---------------------------------------------------------------------------
# 1. The conversion itself
# ---------------------------------------------------------------------------


def test_the_wrapper_is_the_envelope_the_preparer_requires(world) -> None:
    source = json.loads(world["source"].read_bytes())
    assert set(source) == {
        "schema", "builder_policy_id", "source_split_identity_hash", "rows",
    }
    assert source["schema"] == "saea-authored-semantic-knowledge-source-v1"
    assert source["builder_policy_id"] == STAGE3_DELTA_V2_BUILD_POLICY_ID
    assert source["source_split_identity_hash"] == SPLIT


def test_every_row_field_crosses_over_verbatim_and_in_order(world) -> None:
    authored = json.loads(world["authored"].read_bytes())
    source = json.loads(world["source"].read_bytes())
    assert source["rows"] == authored["rows"]  # deep equality, order included
    assert len(source["rows"]) == 6
    for row in source["rows"]:
        assert set(row) == {
            "value_id", "content", "associated_facet_ids", "node_target",
            "source_sample_ids", "provenance_refs", "task_target", "prior_score",
        }
    assert {row["node_target"] for row in source["rows"]} == {
        "perception", "solver", "reviewer", "planner",
    }


def test_the_twin_wraps_the_same_way_and_keeps_its_own_rows(world) -> None:
    twin_authored = json.loads(world["twin_authored"].read_bytes())
    twin_source = json.loads(world["twin_source"].read_bytes())
    assert twin_source["schema"] == "saea-authored-semantic-knowledge-source-v1"
    assert twin_source["builder_policy_id"] == STAGE3_DELTA_V2_BUILD_POLICY_ID
    assert twin_source["rows"] == twin_authored["rows"]
    # The twin's own top-level key (``twin_of_seed``) does not leak into the
    # envelope, whose key set is checked for exact equality by the preparer.
    assert "twin_of_seed" in twin_authored
    assert set(twin_source) == {
        "schema", "builder_policy_id", "source_split_identity_hash", "rows",
    }
    # It IS a form control: at least one row's attachment moved.
    generation = json.loads(world["source"].read_bytes())["rows"]
    assert any(
        twin["associated_facet_ids"] != own["associated_facet_ids"]
        for twin, own in zip(twin_source["rows"], generation)
    )


def test_the_wrap_receipt_pins_both_digests(world) -> None:
    receipt_path = curator.default_source_receipt_path(world["source"])
    receipt = json.loads(receipt_path.read_bytes())
    assert receipt["schema"] == "saea-stage3-delta-source-wrap-receipt-v1"
    assert receipt["authored"]["sha256"] == hashlib.sha256(
        world["authored"].read_bytes()
    ).hexdigest()
    assert receipt["source"]["sha256"] == hashlib.sha256(
        world["source"].read_bytes()
    ).hexdigest()
    assert receipt["authored"]["authored_schema"] == "saea-stage3-authored-deltas-v2"
    assert receipt["authored"]["row_count"] == 6
    assert receipt["builder_policy_id"] == STAGE3_DELTA_V2_BUILD_POLICY_ID
    twin_receipt = json.loads(
        curator.default_source_receipt_path(world["twin_source"]).read_bytes()
    )
    assert twin_receipt["authored"]["twin_of_seed"] == TWIN_SEED


def test_the_wrapper_bytes_are_deterministic(world, tmp_path) -> None:
    first = world["source"].read_bytes()
    again = tmp_path / "again" / "source.json"
    assert (
        source_cli.main(
            ["--authored", str(world["authored"]), "--out", str(again),
             "--source-split-identity-hash", SPLIT]
        )
        == 0
    )
    assert again.read_bytes() == first
    assert b"\r\n" not in first
    assert first == canonical_json_bytes_of(json.loads(first))


def canonical_json_bytes_of(document) -> bytes:
    return json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


@pytest.mark.parametrize(
    "mutation",
    [
        {"schema": "saea-stage3-authored-deltas-v3"},
        {"rows": []},
    ],
)
def test_a_document_that_is_not_an_authored_deltas_document_is_refused(mutation) -> None:
    document = {
        "schema": "saea-stage3-authored-deltas-v2",
        "iteration": 1,
        "rows": [{"value_id": "delta:1:aaaaaaaaaaaa"}],
        **mutation,
    }
    with pytest.raises(curator.Stage3DeltaStoreError):
        curator.build_authored_source_document(
            document, source_split_identity_hash=SPLIT
        )


def test_a_row_with_a_missing_field_is_refused_rather_than_wrapped() -> None:
    row = {
        "value_id": "delta:1:aaaaaaaaaaaa",
        "content": "A statement.",
        "associated_facet_ids": ["alarm_set"],
        "node_target": "solver",
        "source_sample_ids": ["train-1"],
        "provenance_refs": ["advantage:R:train-1:0:1:0"],
        "task_target": "solver:slot-contract:alarm_set",
    }  # no prior_score
    with pytest.raises(curator.Stage3DeltaStoreError):
        curator.build_authored_source_document(
            {"schema": "saea-stage3-authored-deltas-v2", "iteration": 1, "rows": [row]},
            source_split_identity_hash=SPLIT,
        )


def test_a_bad_split_identity_or_builder_cross_check_is_refused(world) -> None:
    document = json.loads(world["authored"].read_bytes())
    with pytest.raises(curator.Stage3DeltaStoreError):
        curator.build_authored_source_document(
            document, source_split_identity_hash="not-a-hash"
        )
    with pytest.raises(curator.Stage3DeltaStoreError):
        curator.build_authored_source_document(
            document,
            source_split_identity_hash=SPLIT,
            builder_policy_id="saea-authored-stage3-deltas-v1",
        )


# ---------------------------------------------------------------------------
# 2. The gap: the curated document itself is not releasable
# ---------------------------------------------------------------------------


def test_the_curated_document_is_refused_as_an_authored_source(world, capsys) -> None:
    """The S3-4s hand-off gap, stated as a test: pinning ``--out-authored``
    is refused -- by the runbook helper first, and by the preparer itself."""

    exit_code, out_path = _run_registration(
        world,
        template=_template(
            world,
            authored_relpath="prepared/SAEA-SLURP-STAGE3-DELTAS-V1/authored-stage3-deltas-v1.json",
            namespace="knowledge/slurp/semantic/stage3-deltas-refused-v1",
            registration_id="SYNTHETIC-STAGE3-DELTAS-REFUSED-V1",
        ),
        out_relpath="stage3-deltas-refused-v1-release-registration",
    )
    assert exit_code == 1
    message = capsys.readouterr().err
    assert "saea-authored-semantic-knowledge-source-v1" in message
    assert "build_slurp_stage3_delta_source.py" in message
    # Nothing was materialised: the refusal is before any write.
    assert not out_path.exists()

    # And directly, without the helper: the preparer refuses the same bytes.
    registration = _template(
        world,
        authored_relpath="prepared/SAEA-SLURP-STAGE3-DELTAS-V1/authored-stage3-deltas-v1.json",
        namespace="knowledge/slurp/semantic/stage3-deltas-refused-v2",
        registration_id="SYNTHETIC-STAGE3-DELTAS-REFUSED-V2",
    )
    registration.pop("template_note")
    registration["source_split_identity_hash"] = SPLIT
    registration["authored_source"]["sha256"] = hashlib.sha256(
        world["authored"].read_bytes()
    ).hexdigest()
    registration["construction_scope"]["sha256"] = world["scope_sha"]
    registration["permitted_roster"]["sha256"] = world["permitted_sha"]
    path = world["repo_root"] / "docs" / "readiness" / "synthetic" / "refused-v2.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(registration))
    with pytest.raises(SemanticKnowledgePreparationError):
        prepare_semantic_knowledge_store(
            path, repo_root=world["repo_root"], data_root=world["data_root"]
        )


def test_a_registration_outside_the_repository_root_is_refused(world) -> None:
    """Why the runbook materialises its runnable registrations into the
    repository: the preparer records one by its repo-relative path."""

    registration = _template(
        world, authored_relpath=GENERATION["authored_relpath"],
        namespace=GENERATION["namespace"], registration_id="SYNTHETIC-OUTSIDE-V1",
    )
    registration.pop("template_note")
    registration["source_split_identity_hash"] = SPLIT
    registration["authored_source"]["sha256"] = hashlib.sha256(
        world["source"].read_bytes()
    ).hexdigest()
    registration["construction_scope"]["sha256"] = world["scope_sha"]
    registration["permitted_roster"]["sha256"] = world["permitted_sha"]
    outside = world["data_root"] / "coordination" / "registration.json"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_bytes(canonical_bytes(registration))
    with pytest.raises(SemanticKnowledgePreparationError, match="repo_root"):
        prepare_semantic_knowledge_store(
            outside, repo_root=world["repo_root"], data_root=world["data_root"]
        )


# ---------------------------------------------------------------------------
# 3. The release, end to end
# ---------------------------------------------------------------------------


def test_the_generation_store_releases_and_round_trips(world) -> None:
    result = _release(world, **GENERATION)
    assert result["cache"] == "cold"
    completion = result["completion"]
    assert completion["contacts"] == {"model": 0, "tool": 0, "scorer": 0}
    namespace = world["data_root"] / GENERATION["namespace"]
    for name in ("snapshot.json", "release.json", "completion.json"):
        assert (namespace / name).is_file()

    release = json.loads((namespace / "release.json").read_text(encoding="utf-8"))
    assert release["builder_policy_id"] == STAGE3_DELTA_V2_BUILD_POLICY_ID
    assert release["source"]["relpath"] == GENERATION["authored_relpath"]
    assert release["source"]["sha256"] == hashlib.sha256(
        world["source"].read_bytes()
    ).hexdigest()

    binding = load_knowledge_store_binding(
        {"knowledge_stores": {"stage3-deltas": _store_spec(completion)}},
        data_root=world["data_root"],
    )
    snapshot = binding.snapshot_for("stage3-deltas")
    authored_rows = {
        row["value_id"]: row
        for row in json.loads(world["source"].read_bytes())["rows"]
    }
    assert {value.value_id for value in snapshot.values} == set(authored_rows)
    for value in snapshot.values:
        row = authored_rows[value.value_id]
        assert value.content == row["content"]
        assert value.task_target == row["task_target"]
        assert value.prior_score == pytest.approx(row["prior_score"])
        assert list(value.associated_facet_ids) == row["associated_facet_ids"]
    assert snapshot.source_sample_ids == CONSTRUCTION_IDS


def test_the_twin_store_releases_into_its_own_namespace(world) -> None:
    result = _release(world, **TWIN)
    completion = result["completion"]
    namespace = world["data_root"] / TWIN["namespace"]
    assert (namespace / "snapshot.json").is_file()
    binding = load_knowledge_store_binding(
        {"knowledge_stores": {"stage3-deltas": _store_spec(completion)}},
        data_root=world["data_root"],
    )
    twin_snapshot = binding.snapshot_for("stage3-deltas")
    twin_rows = {
        row["value_id"]: row
        for row in json.loads(world["twin_source"].read_bytes())["rows"]
    }
    assert {value.value_id for value in twin_snapshot.values} == set(twin_rows)
    for value in twin_snapshot.values:
        assert list(value.associated_facet_ids) == twin_rows[value.value_id][
            "associated_facet_ids"
        ]
    # Same statements, same count: a form control, not a content change.
    generation = _release(world, **GENERATION)["completion"]
    generation_binding = load_knowledge_store_binding(
        {"knowledge_stores": {"stage3-deltas": _store_spec(generation)}},
        data_root=world["data_root"],
    )
    own = generation_binding.snapshot_for("stage3-deltas")
    assert len(twin_snapshot.values) == len(own.values)
    assert {value.content for value in twin_snapshot.values} == {
        value.content for value in own.values
    }


def test_re_releasing_the_same_registration_is_warm_and_byte_identical(world) -> None:
    first = _release(world, **GENERATION)
    second = _release(world, **GENERATION)
    assert first["cache"] == "cold"
    assert second["cache"] == "warm"
    assert first["completion_pin"] == second["completion_pin"]


# ---------------------------------------------------------------------------
# 4. The released snapshot actually serves the four per-node routes
# ---------------------------------------------------------------------------


def _store_spec(completion, *, context_supply=None):
    spec = {
        "store_role": "stage3-deltas",
        "snapshot": completion["snapshot"],
        "release": completion["release"],
    }
    if context_supply is not None:
        spec["context_supply"] = context_supply
    return spec


def _program():
    return PhaseProgram(
        program_id="synthetic-four-node-v1",
        phases=(
            PhaseSpec("perception", "form-candidates", "supplied", None, False),
            PhaseSpec("reviewer", "review-evidence", "supplied", None, False),
            PhaseSpec("planner", "choose-next-action", "supplied", None, False),
            PhaseSpec("solver", "answer", "supplied", None, False),
        ),
        max_contacts=11,
        stop_rule="native-role-episode",
    ).validate()


def _candidate_route(node, cap):
    return {
        "provider": STAGE3_DELTA_CONTEXT_PROVIDER_ID,
        "candidate_state_phase": "perception",
        "cap": cap,
        "rank_by": "prior_score",
        "node_target": node,
    }


ALL_ROUTES = {
    "perception": {
        "provider": STAGE3_DELTA_UNCONDITIONAL_PROVIDER_ID,
        "cap": 4,
        "rank_by": "prior_score",
        "node_target": "perception",
    },
    "reviewer": _candidate_route("reviewer", 4),
    "planner": _candidate_route("planner", 4),
    "solver": _candidate_route("solver", 8),
}


def _perception_state(sample_id, intents):
    content = json.dumps(
        {
            "schema": "saea-slurp-intent-hypotheses-v1",
            "semantics": "ranked-mutually-exclusive-intent-alternatives",
            "sample_id": sample_id,
            "candidates": [
                {
                    "intent_id": intent,
                    "distinction": f"Evidence for {intent}.",
                    "evidence_refs": ["speech"],
                    "unresolved_fields": [],
                }
                for intent in intents
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return AgentStateArtifact(
        state_id=f"perception:{sample_id}",
        state_kind="phase:perception",
        content=content,
        source_query_state_sha256=SHA_B,
        source_response_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        producer_policy_id="synthetic-four-node-v1",
        cited_value_ids=(),
    ).validate()


def _context(binding, artifact, sample_id="s1"):
    query = QueryState(
        query_id=f"query:{sample_id}",
        query_sample_id=sample_id,
        speech_packet_id=f"packet:{sample_id}",
        speech_packet_sha256=SHA_B,
        use_split_identity_hash=SPLIT,
        query_source="speech_features",
    ).validate()
    return AgentRuntimeContext(
        sample_id=sample_id,
        knowledge_snapshot_sha256=binding.binding_sha256,
        catalog_facet_ids=tuple(
            facet.facet_id for facet in binding.composite_snapshot.facets
        ),
        catalog_value_ids=tuple(
            value.value_id for value in binding.composite_snapshot.values
        ),
        query_state=query,
        task_contract="synthetic full legal label and type inventory",
        agent_states=(artifact,),
        prior_response_sha256s=(),
        contact_index=1,
    )


def test_the_released_snapshot_serves_every_per_node_route(world) -> None:
    completion = _release(world, **GENERATION)["completion"]
    binding = load_knowledge_store_binding(
        {"knowledge_stores": {
            "stage3-deltas": _store_spec(completion, context_supply=ALL_ROUTES)
        }},
        data_root=world["data_root"],
    )
    router = build_knowledge_store_supply(
        binding, program=_program(), data_root=world["data_root"],
        legal_candidate_ids=INVENTORY,
    )
    rows = {
        row["value_id"]: row
        for row in json.loads(world["source"].read_bytes())["rows"]
    }

    def _expected(node, targets):
        return {
            f"stage3-deltas::{value_id}"
            for value_id, row in rows.items()
            if row["node_target"] == node
            and set(row["associated_facet_ids"]) & set(targets)
        }

    context = _context(binding, _perception_state("s1", ("alarm_set", "play_music")))
    for node in ("solver", "reviewer", "planner"):
        selected = set(
            router.automatic_for_phase(node, context).fusion_decision.selected_value_ids
        )
        assert selected == _expected(node, ("alarm_set", "play_music")), node
        assert selected, node

    # Perception is the FIRST phase: row-independent, seeded once per flight.
    seeds = router.unconditional_first_phase(speech_packet_bindings={"s1": {}, "s2": {}})
    assert set(seeds) == {"perception"}
    perception_values = {
        f"stage3-deltas::{value_id}"
        for value_id, row in rows.items()
        if row["node_target"] == "perception"
    }
    assert set(seeds["perception"]["s1"]) == perception_values
    assert seeds["perception"]["s1"] == seeds["perception"]["s2"]


def test_the_twin_release_serves_the_same_routes(world) -> None:
    completion = _release(world, **TWIN)["completion"]
    binding = load_knowledge_store_binding(
        {"knowledge_stores": {
            "stage3-deltas": _store_spec(completion, context_supply=ALL_ROUTES)
        }},
        data_root=world["data_root"],
    )
    router = build_knowledge_store_supply(
        binding, program=_program(), data_root=world["data_root"],
        legal_candidate_ids=INVENTORY,
    )
    context = _context(binding, _perception_state("s1", ("alarm_set", "play_music")))
    supplied = {
        node: router.automatic_for_phase(node, context).fusion_decision.selected_value_ids
        for node in ("solver", "reviewer", "planner")
    }
    # The twin is routable (that is the point of a form control) and its
    # attachments differ from the generation store's for at least one node.
    assert any(supplied.values())
    seeds = router.unconditional_first_phase(speech_packet_bindings={"s1": {}})
    assert set(seeds) == {"perception"}


def test_nothing_here_touches_the_real_data_root(world) -> None:
    """Every path this module writes is under pytest's own ``tmp_path``."""

    for key in ("repo_root", "data_root", "authored", "source", "twin_source"):
        assert "speechrl-data" not in str(world[key])
        assert str(world[key]).startswith(str(world["repo_root"].parent))


# ---------------------------------------------------------------------------
# 5. The committed templates and the runbook agree with each other
# ---------------------------------------------------------------------------

PACKAGE = REPO_ROOT / "docs" / "readiness" / "2026-09-22-slurp-stage3-delta-cell-r01-v1"
RUNBOOK = (REPO_ROOT / "scripts" / "flights" / "batch" / "adv1_to_deltas.sh").read_text(
    encoding="utf-8"
)
PREPARED_PREFIX = "prepared/SAEA-SLURP-STAGE3-DELTAS-V1/"


def _committed(name):
    return json.loads((PACKAGE / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "name,namespace",
    [
        (
            "stage3-deltas-v1-release-registration.template.json",
            "knowledge/slurp/semantic/stage3-deltas-v1",
        ),
        (
            "stage3-deltas-twin-v1-release-registration.template.json",
            "knowledge/slurp/semantic/stage3-deltas-twin-v1",
        ),
    ],
)
def test_the_committed_templates_pin_a_wrapped_release_source(name, namespace) -> None:
    template = _committed(name)
    for key in steps.TEMPLATE_KEYS_DROPPED:
        template.pop(key, None)
    assert set(template) == {
        "schema", "registration_id", "carrier_lock_key", "source_partition_role",
        "source_split_identity_hash", "builder_policy_id", "store_id", "store_role",
        "authored_source", "construction_scope", "permitted_roster",
        "forbidden_rosters", "output_namespace",
    }
    assert template["builder_policy_id"] == STAGE3_DELTA_V2_BUILD_POLICY_ID
    assert template["output_namespace"] == namespace
    authored_source = template["authored_source"]
    # The pinned source is the WRAPPER, not the curator's --out-authored
    # document: that is the whole release-path fix.
    assert authored_source["root"] == "data"
    assert authored_source["relpath"].startswith(PREPARED_PREFIX + "source-")
    assert authored_source["sha256"].startswith("PENDING_")
    for pin in template["forbidden_rosters"]:
        assert pin["root"] == "repo"
        assert not pin["sha256"].startswith("PENDING_")


def test_the_runbook_writes_exactly_the_sources_the_templates_pin() -> None:
    """The runbook's source paths and the templates' pins are the same
    documents. Since S3-5 revision v1r the runbook writes them at
    ``$TAG`` rather than at the literal ``v1``, and
    ``adv1_to_deltas_steps.py registration --version-tag`` re-points the
    template's pin the same way, so the two agree at every tag exactly when
    they agree once the tag is substituted back."""

    generation = _committed("stage3-deltas-v1-release-registration.template.json")
    twin = _committed("stage3-deltas-twin-v1-release-registration.template.json")
    for pin in (generation["authored_source"], twin["authored_source"]):
        basename = pin["relpath"][len(PREPARED_PREFIX):]
        tagged = basename.replace("-v1.json", "-$TAG.json")
        assert f"=$PREPARED/{tagged}\n" in RUNBOOK, basename
        assert steps.retag(basename, name="pin", tag="v1r") == basename.replace(
            "-v1.json", "-v1r.json"
        )
    # And it wraps them: the curator's own --out-source for the generation
    # document, the standalone conversion CLI for the twin's derangement.
    assert '--out-source "$SOURCE"' in RUNBOOK
    assert "scripts/build_slurp_stage3_delta_source.py" in RUNBOOK
    assert '--authored "$TWIN_AUTHORED" --out "$TWIN_SOURCE"' in RUNBOOK


def test_the_runbook_materialises_its_registrations_inside_the_repository() -> None:
    """``prepare_semantic_knowledge_store`` records a registration by its
    repo-relative path and refuses one outside ``repo_root`` (proven in
    ``test_a_registration_outside_the_repository_root_is_refused``), so the
    runbook must not write them under the data root."""

    for variable in ("REG=", "TWIN_REG="):
        line = next(
            entry for entry in RUNBOOK.splitlines()
            if entry.startswith(variable) and "TEMPLATE" not in entry
        )
        assert line.startswith(f"{variable}$REPO/docs/readiness/"), line
        assert "$COORD" not in line


def test_the_cell1_value_defaults_match_the_committed_namespaces() -> None:
    """``cell1-values`` reads the four released artifacts by their default
    relpaths, so those defaults must name the namespaces the two committed
    registrations actually release into."""

    helper_source = Path(steps.__file__).read_text(encoding="utf-8")
    for name in (
        "stage3-deltas-v1-release-registration.template.json",
        "stage3-deltas-twin-v1-release-registration.template.json",
    ):
        namespace = _committed(name)["output_namespace"]
        for artifact in ("release.json", "snapshot.json"):
            assert f'default="{namespace}/{artifact}"' in helper_source


# ---------------------------------------------------------------------------
# S3-5 revision v1r: the helper's version tag, content hash and reach step
# ---------------------------------------------------------------------------


def test_retag_moves_a_version_and_refuses_to_guess() -> None:
    assert steps.retag("source-stage3-deltas-v1.json", name="x", tag="v1r") == (
        "source-stage3-deltas-v1r.json"
    )
    assert steps.retag(
        "knowledge/slurp/semantic/stage3-deltas-twin-v1", name="x", tag="v1r"
    ) == "knowledge/slurp/semantic/stage3-deltas-twin-v1r"
    assert steps.retag("SAEA-X-PREPARATION-V1", name="x", tag="V1R", old="V1") == (
        "SAEA-X-PREPARATION-V1R"
    )
    # A file inside a versioned namespace: the version is the last path
    # component ending in -v1, not the basename (the first v1r pass caught
    # its own --snapshot-relpath default on exactly this shape).
    assert steps.retag(
        "knowledge/slurp/semantic/stage3-deltas-v1/snapshot.json", name="x", tag="v1r"
    ) == "knowledge/slurp/semantic/stage3-deltas-v1r/snapshot.json"
    # The identity, and the refusal.
    assert steps.retag("anything-v1", name="x", tag="v1") == "anything-v1"
    with pytest.raises(steps.Adv1DeltaStepError, match="refusing to guess"):
        steps.retag("no-version-here", name="x", tag="v1r")


def test_the_snapshot_value_is_the_content_hash_not_the_file_digest(tmp_path) -> None:
    """Commit fb4d8915: the fragment pin is checked against
    ``KnowledgeSnapshot.content_hash()`` and the release document's own
    ``snapshot_sha256`` -- one number, and NOT the snapshot.json file
    digest, which is a third value because the file carries that hash as a
    field of itself."""

    content = "c" * 64
    release = tmp_path / "release.json"
    snapshot = tmp_path / "snapshot.json"
    release.write_text(json.dumps({"snapshot_sha256": content}), encoding="utf-8")
    snapshot.write_text(
        json.dumps({"snapshot_sha256": content, "values": []}), encoding="utf-8"
    )
    assert steps.snapshot_content_hash(release, snapshot) == content
    assert steps.sha256_file(snapshot) != content

    snapshot.write_text(json.dumps({"snapshot_sha256": "d" * 64}), encoding="utf-8")
    with pytest.raises(steps.Adv1DeltaStepError, match="different snapshot_sha256"):
        steps.snapshot_content_hash(release, snapshot)


def test_supply_reach_counts_the_routable_values_per_node() -> None:
    """The model-free upper bound: a candidate-bound route matches a value
    only when one of its facet ids EQUALS a registered candidate intent, so a
    value whose only facet is a slot type is unreachable on every row."""

    def value(node, facets):
        return {
            "value_id": f"delta:1:{node}{len(facets)}",
            "task_target": f"{node}:slot-contract:whatever",
            "associated_facet_ids": list(facets),
        }

    snapshot = {"values": [
        value("solver", ["alarm_set"]),
        value("solver", ["place_name"]),
        value("reviewer", ["alarm_set", "email_query"]),
        value("perception", ["place_name"]),
    ]}
    report = steps.measure_supply_reach(
        snapshot, legal_intents=frozenset({"alarm_set", "email_query"})
    )
    assert report["solver"]["values"] == 2
    assert report["solver"]["reachable_by_a_candidate_intent"] == 1
    assert report["reviewer"]["distinct_intents_covered"] == 2
    assert report["perception"]["reachable_by_a_candidate_intent"] == 0
    assert report["total"]["reachable_by_a_candidate_intent"] == 2
    assert report["per_intent_facet_histogram"] == {"alarm_set": 2, "email_query": 1}
