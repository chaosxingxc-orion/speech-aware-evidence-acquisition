"""The opt-in ``sealed-samples-manifest`` predecessor binding.

Two obligations, and the second is the load-bearing one:

1. the NEW binding does what cell VERIFY-1 needs -- all N sealed grouped-Solver
   candidates of a row, in a permutation pinned by the config, with no
   delivered-answer anchor -- and REFUSES, by name, every malformed custody
   shape this study can state in advance;
2. every already-flown ``sealed-manifest`` cell is BYTE-IDENTICAL. The two
   literals below were measured on the UNMODIFIED tree before the binding
   existed (``acc9da6d...`` over the config-layer bytes of all 35 committed
   sealed-manifest baselines, and ``3b2efbcd...`` / ``200b312b...`` over a
   hermetic render), so a match here is not a circular one.

Zero model, tokenizer, encoder, scorer, server and network contacts; no
``SPEECHRL_DATA_DIR`` read -- the sealed bundle is a stub, and the REAL sealed
ROLL-1 bundle is exercised by the package's own dry run.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.phase_material import (
    PREDECESSOR_BINDINGS,
    SEALED_SAMPLES_BINDING,
    SEALED_SAMPLES_HEADER,
    SEALED_SAMPLES_MAX_COUNT,
    SEALED_SAMPLES_MIN_COUNT,
    SEALED_SAMPLES_STATE_KIND,
    PhaseMaterialError,
    PhaseMaterialSpec,
    build_material_for_phase,
    load_phase_material_specs,
    load_sealed_sample_groups,
    phase_material_receipt,
    render_sealed_sample_block,
    sealed_sample_permutation,
    sealed_sample_states_from_manifest,
    sealed_states_for_spec,
    sealed_states_from_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE = REPO_ROOT / "configs" / "baseline"

#: Measured on the unmodified tree, BEFORE this binding existed.
PRE_CHANGE_SEALED_MANIFEST_AGGREGATE = (
    "acc9da6df5ae08bf4bf15b87ac94d93726e7c9135c5350571165baf652568a15"
)
PRE_CHANGE_HERMETIC_INSTRUCTION = (
    "3b2efbcd30fa1a37160524d9ba8793d0915d8ec8ef355acad283c30193351512"
)
PRE_CHANGE_HERMETIC_RECEIPT = (
    "200b312bfb876da1cfacb2f52a7f5b164077ca0ca8d2ef258df315fdb0d47c0e"
)

SEED = 20260925
COUNT = 5


def _canonical(document: object) -> str:
    return json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def _canonical_sha256(document: object) -> str:
    return hashlib.sha256(_canonical(document).encode("utf-8")).hexdigest()


class _Bundle:
    def __init__(self, rows):
        self.manifest = {"schema": "saea-run-manifest-v1", "status": "COMPLETED"}
        self.outputs_rows = rows


class _Ctx:
    def __init__(self, sample_id):
        self.sample_id = sample_id


def _sample(index, *, scenario="alarm", action="set", entities=(), status="ok"):
    record = {
        "sample_index": index,
        "parse_status": status,
        "seed": 1000 + index,
        "temperature": 0.7,
        "contacts": [f"c{index}"],
        "parsed_answer": {
            "scenario": scenario,
            "action": action,
            "entities": [{"type": t, "filler": f} for t, f in entities],
        },
    }
    if status != "ok":
        record["parsed_answer"] = None
    return record


def _row(sample_id, samples, **extra):
    row = {
        "sample_id": sample_id,
        "text": "the delivered answer nobody may see here",
        "request_sha256": hashlib.sha256(f"req:{sample_id}".encode()).hexdigest(),
        "response_sha256": hashlib.sha256(f"raw:{sample_id}".encode()).hexdigest(),
        "response_text_sha256": hashlib.sha256(f"res:{sample_id}".encode()).hexdigest(),
        "solver_group": {
            "commit_policy_id": "saea-commit-plurality-support-v1",
            "commit_params": {"min_support": 3},
            "delivered": {"sample_index": 0},
            "samples": samples,
        },
    }
    row.update(extra)
    return row


def _five(sample_id, *, distinct=True, status=("ok",) * COUNT):
    return _row(
        sample_id,
        [
            _sample(
                index,
                action=f"set{index}" if distinct else "set",
                status=status[index],
            )
            for index in range(COUNT)
        ],
    )


def _manifest(tmp_path: Path) -> tuple[Path, str]:
    path = tmp_path / "rollout.run-manifest.json"
    path.write_text(json.dumps({"schema": "saea-run-manifest-v1"}), encoding="utf-8")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def _load(tmp_path, rows, **kwargs):
    path, digest = _manifest(tmp_path)
    options = {
        "expected_sha256": digest,
        "phase_name": "choose",
        "producer_policy_id": "SAEA-ROLLOUT-V1",
        "sample_ids": tuple(row["sample_id"] for row in rows),
        "expected_sample_count": COUNT,
        "permutation_seed": SEED,
        "bundle_verifier": lambda _p: _Bundle(rows),
    }
    options.update(kwargs)
    return load_sealed_sample_groups(path, **options)


def _spec(**overrides):
    source = {
        "manifest_relpath": "runs/X/x.run-manifest.json",
        "manifest_sha256": "a" * 64,
        "producer_policy_id": "SAEA-ROLLOUT-V1",
        "expected_sample_count": COUNT,
        "permutation_seed": SEED,
    }
    source.update(overrides.pop("source", {}))
    fields = {
        "phase": "choose",
        "purpose": "select-candidate-answer",
        "instruction_template": "probes/slurp_verify_select_v1.txt",
        "predecessor_binding": SEALED_SAMPLES_BINDING,
        "predecessor_source": source,
    }
    fields.update(overrides)
    return PhaseMaterialSpec(**fields)


# ---------------------------------------------------------------------------
# 1. The vocabulary and the spec-level refusals
# ---------------------------------------------------------------------------


def test_the_binding_is_registered_beside_the_three_that_existed():
    assert SEALED_SAMPLES_BINDING == "sealed-samples-manifest"
    assert PREDECESSOR_BINDINGS == {
        "none",
        "append-sealed-state",
        "sealed-manifest",
        SEALED_SAMPLES_BINDING,
    }


def test_a_well_formed_spec_validates_and_round_trips():
    spec = _spec().validate()
    document = spec.as_json()
    assert document["predecessor_binding"] == SEALED_SAMPLES_BINDING
    assert document["predecessor_source"]["permutation_seed"] == SEED
    assert document["predecessor_source"]["expected_sample_count"] == COUNT


@pytest.mark.parametrize(
    "source,expected",
    [
        ({"permutation_seed": None}, "permutation_seed must be a non-negative integer"),
        ({"permutation_seed": -1}, "permutation_seed must be a non-negative integer"),
        ({"permutation_seed": True}, "permutation_seed must be a non-negative integer"),
        ({"permutation_seed": "20260925"}, "permutation_seed must be a non-negative"),
        ({"expected_sample_count": 1}, "expected_sample_count must be an integer from"),
        ({"expected_sample_count": 99}, "expected_sample_count must be an integer from"),
        ({"expected_sample_count": True}, "expected_sample_count must be an integer"),
        ({"manifest_relpath": ""}, "predecessor_source.manifest_relpath must be a"),
        ({"producer_policy_id": " "}, "predecessor_source.producer_policy_id must be a"),
    ],
)
def test_a_malformed_source_key_is_refused_by_name(source, expected):
    with pytest.raises(PhaseMaterialError, match=expected):
        _spec(source=source).validate()


def test_a_missing_permutation_seed_is_refused_as_a_key_set_violation():
    source = {
        "manifest_relpath": "runs/X/x.run-manifest.json",
        "manifest_sha256": "a" * 64,
        "producer_policy_id": "SAEA-ROLLOUT-V1",
        "expected_sample_count": COUNT,
    }
    with pytest.raises(PhaseMaterialError, match="with exactly"):
        PhaseMaterialSpec(
            phase="choose",
            purpose="select-candidate-answer",
            instruction_template="probes/slurp_verify_select_v1.txt",
            predecessor_binding=SEALED_SAMPLES_BINDING,
            predecessor_source=source,
        ).validate()


def test_an_extra_source_key_is_refused():
    with pytest.raises(PhaseMaterialError, match="with exactly"):
        _spec(source={"gold_relpath": "x"}).validate()


def test_the_sealed_manifest_key_set_is_still_refused_for_the_new_binding():
    """The two bindings carry DIFFERENT exact key sets, so the three-key
    ``sealed-manifest`` source is not silently accepted here."""

    with pytest.raises(PhaseMaterialError, match="with exactly"):
        PhaseMaterialSpec(
            phase="choose",
            purpose="select-candidate-answer",
            instruction_template="probes/slurp_verify_select_v1.txt",
            predecessor_binding=SEALED_SAMPLES_BINDING,
            predecessor_source={
                "manifest_relpath": "runs/X/x.run-manifest.json",
                "manifest_sha256": "a" * 64,
                "producer_policy_id": "SAEA-ROLLOUT-V1",
            },
        ).validate()


def test_a_state_fill_beside_the_new_binding_is_refused():
    with pytest.raises(PhaseMaterialError, match="candidate BLOCK"):
        _spec(state_fill="slurp-intent-slot-schema-for-state").validate()


def test_the_binding_is_refused_beside_prepared_execution_units():
    program = default_phase_program("phase-slurp-verify-select-v1")
    values = {
        "prepared_execution_units": {"relpath": "x", "sha256": "b" * 64},
        "phase_material": {
            "choose": {
                "instruction_template": "probes/slurp_verify_select_v1.txt",
                "response_format_id": "slurp-verifier-choice-v1",
                "predecessor_binding": SEALED_SAMPLES_BINDING,
                "predecessor_source": _spec().predecessor_source,
            }
        },
    }
    with pytest.raises(PhaseMaterialError, match="execution windows require"):
        load_phase_material_specs(values, program)


# ---------------------------------------------------------------------------
# 2. The permutation
# ---------------------------------------------------------------------------


def test_the_permutation_is_a_permutation_and_is_deterministic():
    first = sealed_sample_permutation("slurp:train:000049:audio-1", seed=SEED, count=COUNT)
    second = sealed_sample_permutation("slurp:train:000049:audio-1", seed=SEED, count=COUNT)
    assert first == second
    assert sorted(first) == list(range(COUNT))


def test_the_permutation_is_per_row_and_seed_sensitive():
    rows = [f"slurp:train:{index:06d}:audio-{index}" for index in range(200)]
    orders = {sealed_sample_permutation(row, seed=SEED, count=COUNT) for row in rows}
    # Per ROW, not per run: one shared order would confound position bias with
    # sample-index bias, which is what the single-answer control measures.
    assert len(orders) > 50
    assert sealed_sample_permutation(rows[0], seed=SEED, count=COUNT) != (
        sealed_sample_permutation(rows[0], seed=SEED + 1, count=COUNT)
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"seed": -1},
        {"seed": True},
        {"seed": "20260925"},
        {"count": 0},
        {"count": True},
    ],
)
def test_the_permutation_refuses_a_malformed_draw(kwargs):
    options = {"seed": SEED, "count": COUNT}
    options.update(kwargs)
    with pytest.raises(PhaseMaterialError):
        sealed_sample_permutation("slurp:train:000049:audio-1", **options)


def test_the_permutation_needs_a_sample_id():
    with pytest.raises(PhaseMaterialError, match="needs a sample id"):
        sealed_sample_permutation("", seed=SEED, count=COUNT)


# ---------------------------------------------------------------------------
# 3. The rendered block
# ---------------------------------------------------------------------------


def test_the_block_numbers_every_candidate_from_one():
    block = render_sealed_sample_block(("A", "B", "C"))
    assert block.splitlines() == [
        f"{SEALED_SAMPLES_HEADER} [3 candidates]:",
        "1. A",
        "2. B",
        "3. C",
    ]


def test_the_block_refuses_an_empty_candidate():
    with pytest.raises(PhaseMaterialError, match="non-empty rendered candidate"):
        render_sealed_sample_block(("A", "  "))
    with pytest.raises(PhaseMaterialError, match="non-empty rendered candidate"):
        render_sealed_sample_block(())


def test_the_block_never_carries_the_delivered_answer(tmp_path):
    rows = [_five("s1")]
    groups = _load(tmp_path, rows)
    content = groups["s1"].state.content
    assert rows[0]["text"] not in content
    assert content.count(SEALED_SAMPLES_HEADER) == 1
    assert len([line for line in content.splitlines() if line[:2] in
                ("1.", "2.", "3.", "4.", "5.")]) == COUNT


def test_the_state_records_the_permutation_and_its_own_kind(tmp_path):
    groups = _load(tmp_path, [_five("s1")])
    group = groups["s1"]
    assert group.state.state_kind == f"phase:choose:{SEALED_SAMPLES_STATE_KIND}"
    assert group.state.cited_value_ids == tuple(
        f"solver-sample-{index}-at-position-{position + 1}"
        for position, index in enumerate(group.permutation)
    )
    assert group.state.source_query_state_sha256 == _five("s1")["request_sha256"]


def test_the_positions_carry_the_permuted_candidates(tmp_path):
    groups = _load(tmp_path, [_five("s1")])
    group = groups["s1"]
    # position i shows the candidate of sealed sample permutation[i]
    for position, index in enumerate(group.permutation):
        assert f'"action": "set{index}"' in group.rendered[position]


# ---------------------------------------------------------------------------
# 4. The custody refusals
# ---------------------------------------------------------------------------


def test_a_row_without_solver_group_is_refused(tmp_path):
    row = _five("s1")
    del row["solver_group"]
    with pytest.raises(PhaseMaterialError, match="carries no solver_group custody"):
        _load(tmp_path, [row])


def test_a_row_whose_sample_count_differs_is_refused(tmp_path):
    row = _five("s1")
    row["solver_group"]["samples"] = row["solver_group"]["samples"][:4]
    with pytest.raises(PhaseMaterialError, match="not the registered 5"):
        _load(tmp_path, [row])


def test_a_row_with_a_duplicate_sample_index_is_refused(tmp_path):
    row = _five("s1")
    row["solver_group"]["samples"][4]["sample_index"] = 3
    with pytest.raises(PhaseMaterialError, match="two solver samples with sample_index"):
        _load(tmp_path, [row])


def test_a_row_with_a_non_integer_sample_index_is_refused(tmp_path):
    row = _five("s1")
    row["solver_group"]["samples"][2]["sample_index"] = "2"
    with pytest.raises(PhaseMaterialError, match="without an integer sample_index"):
        _load(tmp_path, [row])


def test_an_unknown_parse_status_is_refused(tmp_path):
    row = _five("s1")
    row["solver_group"]["samples"][1]["parse_status"] = "partial"
    with pytest.raises(PhaseMaterialError, match="carries parse_status 'partial'"):
        _load(tmp_path, [row])


@pytest.mark.parametrize(
    "where,key",
    [
        ("row", "gold_answer"),
        ("row", "reference_text"),
        ("group", "annotation"),
        ("record", "expected_entities"),
        ("record", "target"),
    ],
)
def test_a_reference_shaped_key_is_refused_rather_than_read_around(tmp_path, where, key):
    row = _five("s1")
    if where == "row":
        row[key] = "x"
    elif where == "group":
        row["solver_group"][key] = "x"
    else:
        row["solver_group"]["samples"][0][key] = "x"
    with pytest.raises(PhaseMaterialError, match="reference-shaped key"):
        _load(tmp_path, [row])


def test_a_manifest_hash_mismatch_is_refused(tmp_path):
    with pytest.raises(PhaseMaterialError, match="hashes to"):
        _load(tmp_path, [_five("s1")], expected_sha256="c" * 64)


def test_a_duplicate_row_is_refused(tmp_path):
    with pytest.raises(PhaseMaterialError, match="duplicate rows"):
        _load(tmp_path, [_five("s1"), _five("s1")], sample_ids=("s1",))


def test_a_requested_row_the_bundle_lacks_is_refused(tmp_path):
    with pytest.raises(PhaseMaterialError, match="has no row for"):
        _load(tmp_path, [_five("s1")], sample_ids=("s1", "s2"))


def test_an_out_of_range_expected_count_is_refused(tmp_path):
    with pytest.raises(PhaseMaterialError, match="expected_sample_count from"):
        _load(tmp_path, [_five("s1")], expected_sample_count=1)


# ---------------------------------------------------------------------------
# 5. An unparseable sample: the row FLIES, five candidates still render
# ---------------------------------------------------------------------------


def test_an_unparseable_sample_renders_the_canonical_empty_answer(tmp_path):
    from speech_aware_evidence_acquisition.rails.stage3_advantage_material import (
        EMPTY_ANSWER,
    )

    status = ["ok"] * COUNT
    status[2] = "malformed"
    groups = _load(tmp_path, [_five("s1", status=tuple(status))])
    group = groups["s1"]
    assert group.parse_ok == COUNT - 1
    assert group.parse_failed == 1
    # The registered candidate count is unchanged: no row is ever shown fewer.
    assert len(group.rendered) == COUNT
    assert EMPTY_ANSWER in group.rendered
    position = group.permutation.index(2)
    assert group.rendered[position] == EMPTY_ANSWER


def test_the_distinct_answer_count_is_content_not_position(tmp_path):
    groups = _load(tmp_path, [_five("s1", distinct=False)])
    assert groups["s1"].distinct_answers == 1
    groups = _load(tmp_path, [_five("s2")])
    assert groups["s2"].distinct_answers == COUNT


def test_the_group_receipt_carries_counts_and_hashes_only(tmp_path):
    document = _load(tmp_path, [_five("s1")])["s1"].as_json()
    assert set(document) == {
        "sample_id",
        "permutation",
        "rendered_sha256",
        "parse_ok",
        "parse_failed",
        "distinct_answers",
        "state_content_sha256",
    }
    assert all(len(item) == 64 for item in document["rendered_sha256"])


# ---------------------------------------------------------------------------
# 6. The single dispatch seam
# ---------------------------------------------------------------------------


def test_sealed_states_for_spec_loads_nothing_for_an_internal_binding(tmp_path):
    for binding in ("none", "append-sealed-state"):
        spec = PhaseMaterialSpec(
            phase="choose",
            purpose="select-candidate-answer",
            instruction_template="probes/slurp_verify_select_v1.txt",
            predecessor_binding=binding,
        ).validate()
        assert (
            sealed_states_for_spec(
                spec, data_root=tmp_path, phase_name="choose", sample_ids=("s1",)
            )
            is None
        )


def test_sealed_states_for_spec_dispatches_the_new_binding(tmp_path):
    rows = [_five("s1")]
    path, digest = _manifest(tmp_path)
    spec = _spec(
        source={"manifest_relpath": path.name, "manifest_sha256": digest}
    ).validate()
    states = sealed_states_for_spec(
        spec,
        data_root=tmp_path,
        phase_name="choose",
        sample_ids=("s1",),
        bundle_verifier=lambda _p: _Bundle(rows),
    )
    assert set(states) == {"s1"}
    assert SEALED_SAMPLES_HEADER in states["s1"].content


def test_sealed_states_for_spec_dispatches_the_old_binding(tmp_path):
    rows = [_five("s1")]
    path, digest = _manifest(tmp_path)
    spec = PhaseMaterialSpec(
        phase="slots",
        purpose="fill-slots",
        instruction_template="probes/slurp_phase_slots.txt",
        predecessor_binding="sealed-manifest",
        predecessor_source={
            "manifest_relpath": path.name,
            "manifest_sha256": digest,
            "producer_policy_id": "phase-direct-only-v1",
        },
    ).validate()
    states = sealed_states_for_spec(
        spec,
        data_root=tmp_path,
        phase_name="slots",
        sample_ids=("s1",),
        bundle_verifier=lambda _p: _Bundle(rows),
    )
    # The OLD binding still binds the row's DELIVERED text and nothing else.
    assert states["s1"].content == rows[0]["text"]
    assert states["s1"].state_kind == "phase:slots"


def test_the_states_helper_is_the_same_object_the_group_loader_builds(tmp_path):
    rows = [_five("s1"), _five("s2")]
    path, digest = _manifest(tmp_path)
    options = {
        "expected_sha256": digest,
        "phase_name": "choose",
        "producer_policy_id": "SAEA-ROLLOUT-V1",
        "sample_ids": ("s1", "s2"),
        "expected_sample_count": COUNT,
        "permutation_seed": SEED,
        "bundle_verifier": lambda _p: _Bundle(rows),
    }
    states = sealed_sample_states_from_manifest(path, **options)
    groups = load_sealed_sample_groups(path, **options)
    assert {key: value.as_json() for key, value in states.items()} == {
        key: value.state.as_json() for key, value in groups.items()
    }


# ---------------------------------------------------------------------------
# 7. The material the phase runner actually builds
# ---------------------------------------------------------------------------


def test_the_block_is_appended_after_the_instruction(tmp_path):
    rows = [_five("s1")]
    groups = _load(tmp_path, rows)
    specs = {"choose": _spec().validate()}
    material = build_material_for_phase(
        specs,
        program_id="phase-slurp-verify-select-v1",
        static_text_by_phase={"choose": "INSTRUCTION."},
        response_format_by_phase={},
        per_sample_states={"choose": {"s1": groups["s1"].state}},
    )
    built = material("choose", _Ctx("s1"), {})
    assert built.instruction.startswith("INSTRUCTION.\n\nPrior phase response (")
    assert built.instruction.endswith(groups["s1"].state.content)
    assert built.contact_id == "phase-slurp-verify-select-v1:choose:s1"


def test_a_row_with_no_loaded_state_is_refused(tmp_path):
    specs = {"choose": _spec().validate()}
    material = build_material_for_phase(
        specs,
        program_id="phase-slurp-verify-select-v1",
        static_text_by_phase={"choose": "INSTRUCTION."},
        response_format_by_phase={},
        per_sample_states={"choose": {}},
    )
    with pytest.raises(PhaseMaterialError, match="predecessor but no state was loaded"):
        material("choose", _Ctx("s1"), {})


# ---------------------------------------------------------------------------
# 8. BYTE IDENTITY of every sealed-manifest cell that existed before
# ---------------------------------------------------------------------------


def test_every_committed_sealed_manifest_cell_composes_to_the_pre_change_bytes():
    measured = {}
    for path in sorted(BASELINE.glob("*.json")):
        raw = path.read_text(encoding="utf-8")
        if "sealed-manifest" not in raw:
            continue
        values = json.loads(raw)
        program = default_phase_program(str(values["policy"]))
        specs = load_phase_material_specs(values, program)
        measured[path.name] = _canonical_sha256(
            {phase: spec.as_json() for phase, spec in sorted(specs.items())}
        )
    assert len(measured) == 35
    assert _canonical_sha256(measured) == PRE_CHANGE_SEALED_MANIFEST_AGGREGATE


def test_a_hermetic_sealed_manifest_render_is_byte_identical(tmp_path):
    rows = [
        {
            "sample_id": f"slurp:train:{index:06d}:audio-{index}",
            "text": json.dumps(
                {"scenario": "alarm", "action": "set", "entities": []}, sort_keys=True
            ),
            "request_sha256": hashlib.sha256(f"req{index}".encode()).hexdigest(),
            "response_text_sha256": hashlib.sha256(f"res{index}".encode()).hexdigest(),
        }
        for index in range(3)
    ]
    path, digest = _manifest(tmp_path)
    states = sealed_states_from_manifest(
        path,
        expected_sha256=digest,
        phase_name="slots",
        producer_policy_id="phase-direct-only-v1",
        sample_ids=tuple(row["sample_id"] for row in rows),
        bundle_verifier=lambda _p: _Bundle(rows),
    )
    spec = PhaseMaterialSpec(
        phase="slots",
        purpose="fill-slots",
        instruction_template="probes/slurp_phase_slots.txt",
        predecessor_binding="sealed-manifest",
        predecessor_source={
            "manifest_relpath": "runs/X/x.run-manifest.json",
            "manifest_sha256": digest,
            "producer_policy_id": "phase-direct-only-v1",
        },
    ).validate()
    specs = {"slots": spec}
    static = {"slots": "STATIC INSTRUCTION TEXT."}
    material = build_material_for_phase(
        specs,
        program_id="phase-slots-given-intent-v1",
        static_text_by_phase=static,
        response_format_by_phase={},
        per_sample_states={"slots": states},
    )
    for row in rows:
        built = material("slots", _Ctx(row["sample_id"]), {})
        assert (
            hashlib.sha256(built.instruction.encode("utf-8")).hexdigest()
            == PRE_CHANGE_HERMETIC_INSTRUCTION
        )
        assert states[row["sample_id"]].state_kind == "phase:slots"
    assert (
        _canonical_sha256(phase_material_receipt(specs, static, {}))
        == PRE_CHANGE_HERMETIC_RECEIPT
    )


def test_the_bounds_are_the_registered_ones():
    assert (SEALED_SAMPLES_MIN_COUNT, SEALED_SAMPLES_MAX_COUNT) == (2, 16)


def test_balanced_binding_uses_full_source_for_smoke_and_main(tmp_path):
    rows = [_five(f"r{i}") for i in range(25)]
    full = _load(tmp_path, rows, permutation_rule="balanced-block-v1")
    subset = _load(tmp_path, rows, sample_ids=("r2", "r17"),
                   permutation_rule="balanced-block-v1")
    assert subset["r2"] == full["r2"]
    assert subset["r17"] == full["r17"]
    path, digest = _manifest(tmp_path)
    spec = _spec(source={"manifest_relpath": path.name, "manifest_sha256": digest,
                         "permutation_rule": "balanced-block-v1"}).validate()
    states = sealed_states_for_spec(spec, data_root=tmp_path, phase_name="choose",
                                   sample_ids=("r2",), bundle_verifier=lambda _p: _Bundle(rows))
    assert states["r2"] == full["r2"].state
