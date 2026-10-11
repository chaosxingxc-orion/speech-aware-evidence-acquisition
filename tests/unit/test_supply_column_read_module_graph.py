"""Loop engineering item E-S2: the readers read a supply column flown under the review-off module graph.

A synthetic sealed run is built exactly as the instrument seals one: the consumption module's ``supply``
columns (E-S1) compile the Solver's ``supply_variants`` block (arms ``typ`` re-cap, ``ace`` release swap,
the twin ``aa`` and the delivering ``lock``); the loader parses it into the arm group; every row holds the
review-off episode (a Perception visit and a Solver visit only), the v3 receipt and one trace pair per arm.
The node-local reader (``slurp_nx_solver_column_read``), the official column renderer
(``stage3_rollout_score``'s ``--mode supply-variants`` render) and the v4 applier's ``--column`` loader are
driven on it. Model-free; no scorer subprocess.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_consumption_module_review_off import review_off_block
from test_slurp_nx_solver_column_read import ANSWERS, GOLD, SECRET, _gold_map

_REPO = Path(__file__).resolve().parents[2]
for _extra in (_REPO / "scripts" / "analysis",):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import slurp_nx_solver_column_read as reader  # noqa: E402

from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails import controllers  # noqa: E402,F401 - registers formats
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import (  # noqa: E402
    carrier_module_hooks,
)
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program  # noqa: E402
from speech_aware_evidence_acquisition.rails.native_episode_config import (  # noqa: E402
    load_native_episode_config,
)
from speech_aware_evidence_acquisition.rails.supply_variants import (  # noqa: E402
    supply_variant_arm_record,
    supply_variant_receipt,
)

_spec = importlib.util.spec_from_file_location(
    "stage3_supply_module_graph_score", _REPO / "scripts/analysis/stage3_rollout_score.py")
score_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(score_mod)

FIT = {
    "slot_tokens": 24576, "completion_ceiling": 640,
    "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120,
}
EX_K = "knowledge_stores.train-exemplars.phase_supply.solver.k"
ALT_RELEASE = "knowledge/slurp/alt/release.json"
ARMS = ("typ", "ace", "aa", "lock")
#: the arms' answers: typ = the template test's t1, ace = its t2, the twin = the delivering arm.
SUPPLY_ANSWERS = {"typ": ANSWERS["t1"], "ace": ANSWERS["t2"], "aa": ANSWERS["lock"], "lock": ANSWERS["lock"]}
#: sealed supplied ids per arm (ids only): typ drops one item, ace adds one, the twin equals the delivering arm.
SUPPLIED = {
    "lock": ("v:a", "v:b", "v:c"), "aa": ("v:a", "v:b", "v:c"),
    "typ": ("v:a", "v:b"), "ace": ("v:a", "v:x", "v:b", "v:c"),
}


def _block():
    block = review_off_block()
    block["columns"] = [
        {"column_id": "typ", "kind": "supply", "node": "solver", "max_supplied_items": 40,
         "overrides": {EX_K: 10}},
        {"column_id": "ace", "kind": "supply", "node": "solver", "max_supplied_items": 55,
         "release_swap": {"store_id": "train-exemplars", "release": ALT_RELEASE}},
    ]
    block["supply_frame"] = {
        "twin": True, "fit_estimate": dict(FIT), "delivering_max_supplied_items": 55,
        "alternates": {"train-exemplars": [{
            "release": {"relpath": ALT_RELEASE, "sha256": "a" * 64},
            "snapshot": {"relpath": "knowledge/slurp/alt/snapshot.json", "sha256": "b" * 64},
        }]},
    }
    return block


def _values():
    block = _block()
    values = cm.compile_module(block, carrier_module_hooks()).values()
    values["carrier_lock_key"] = "slurp"
    values["native_episode"]["consumption_module"] = block
    return values


def _group(values=None):
    values = _values() if values is None else values
    return load_native_episode_config(values, default_phase_program(values["policy"])).supply_variant_group


def _sealed(*, rows=None, group=None):
    group = _group() if group is None else group
    outputs, trace = [], {}
    for sid in rows or sorted(GOLD):
        contacts = []
        for index, arm_id in enumerate(group.arm_ids):
            rid = f"{sid}/{arm_id}"
            raw = SUPPLY_ANSWERS[arm_id][sid]
            contact = {
                "agent_contact_id": f"solver:{sid}:{index}", "request_id": rid,
                "request_sha256": hashlib.sha256(rid.encode()).hexdigest(),
                "response_sha256": hashlib.sha256(("envelope" + rid).encode()).hexdigest(),
                "response_text_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            }
            contacts.append(contact)
            trace[rid + "/request"] = {"payload_sha256": contact["request_sha256"]}
            trace[rid + "/response"] = {"text": raw, "response_text_sha256": contact["response_text_sha256"]}
        records = [
            supply_variant_arm_record(
                arm=arm, arm_index=i, contact_id=contacts[i]["agent_contact_id"],
                supplied_value_ids=SUPPLIED[arm.arm_id],
            )
            for i, arm in enumerate(group.arms)
        ]
        receipt = supply_variant_receipt(group=group, phase_id="solver", records=records)
        # the review-off module graph: a Perception visit and ONE Solver visit, no Reviewer or Planner
        visits = [
            {"role_id": "perception", "stage": "perception",
             "execution_receipt": {"contacts": [], "final_contact": None}},
            {"role_id": "solver", "stage": "solver",
             "execution_receipt": {"contacts": contacts, "final_contact": contacts[-1]}},
        ]
        outputs.append({"sample_id": sid, "supply_variants": receipt,
                        "native_episode_receipt": {"role_visits": visits, "kind": "accepted"}})
    return outputs, trace


# ---------------------------------------------------------------------------
# the node-local reader


def test_the_loader_reads_the_module_graph_supply_column():
    outputs, trace = _sealed()
    sealed = reader.load_sealed_arm_texts(outputs, trace)
    assert sealed["kind"] == "supply" and sealed["arm_ids"] == ARMS
    assert sealed["delivering"] == "lock" and sealed["twin"] == "aa"
    assert sealed["templates"][0] == {
        "resolved_knobs": [{"path": EX_K, "value": 10}], "release_swap": None, "max_supplied_items": 40}
    assert sealed["templates"][1]["release_swap"] == {"store_id": "train-exemplars", "release": ALT_RELEASE}
    assert sealed["templates"][2]["release_swap"] is None and sealed["templates"][3]["resolved_knobs"] == []
    assert sealed["texts"]["typ"] == ANSWERS["t1"]
    assert sealed["supplied_ids"]["ace"]["slurp:train:1:a"] == list(SUPPLIED["ace"])
    assert sealed["rows_without_solver_visit"] == []


def _read(**kwargs):
    outputs, trace = _sealed()
    sealed = reader.load_sealed_arm_texts(outputs, trace)
    return reader.read_columns(
        sealed["texts"], _gold_map(), arm_ids=sealed["arm_ids"], delivering=sealed["delivering"],
        twin=sealed["twin"], draws=200, group_kind=sealed["kind"], supplied_ids=sealed["supplied_ids"],
        **kwargs,
    )


def test_the_supply_column_is_read_like_a_template_column_with_the_supply_statistics():
    report = _read()
    assert report["arm_group_kind"] == "supply" and report["arm_order"] == list(ARMS)
    # the paired counts are the template reader's own (typ = t1 vs the delivering arm)
    exact = report["arms"]["typ"]["paired_vs_delivering"]["exact_set"]
    assert (exact["n"], exact["b_arm_only"], exact["c_delivering_only"]) == (6, 3, 1)
    fill = report["arms"]["typ"]["paired_vs_delivering"]["empty_gold_false_fill"]
    assert fill["n"] == 2 and fill["diff_pp"] == pytest.approx(-50.0)
    nonempty = report["arms"]["typ"]["paired_vs_delivering"]["nonempty_exact"]
    assert nonempty["n"] == 4 and (nonempty["b_arm_only"], nonempty["c_delivering_only"]) == (2, 1)
    # the twin is the delivering arm's replicate: zero difference, the role says so
    assert report["arms"]["aa"]["role"] == "twin"
    assert report["arms"]["aa"]["paired_vs_delivering"]["exact_set"]["diff_pp"] == 0.0
    assert report["arms"]["lock"]["paired_vs_delivering"] == {}
    assert set(report["mechanical_screen"]) == {"typ", "ace"}
    assert report["arms"]["typ"]["by_slot_type"]["date"]["gold_items"] == 3
    # the supply statistics, from the sealed ids only (six rows)
    stats = report["supply_stats"]
    assert stats["lock"] == {"rows": 6, "items_total": 18, "items_mean": 3.0, "rows_with_no_items": 0}
    assert stats["typ"]["items_total"] == 12 and stats["typ"]["items_removed_vs_delivering"] == 6
    assert stats["typ"]["items_added_vs_delivering"] == 0 and stats["typ"]["rows_same_id_set"] == 0
    assert stats["ace"]["items_total"] == 24 and stats["ace"]["items_added_vs_delivering"] == 6
    assert stats["ace"]["items_removed_vs_delivering"] == 0 and stats["ace"]["items_added_mean"] == 1.0
    assert stats["aa"]["rows_same_id_set"] == 6 and stats["aa"]["items_added_vs_delivering"] == 0
    assert stats["aa"]["rows_same_set_other_order"] == 0


def test_the_supply_tables_render_with_the_supply_section_and_no_text():
    report = _read()
    table = reader.render(report)
    assert "## Supply columns: supplied items and id-set difference" in table
    assert "| ace |" in table and "NORMALISED (primary)" in table
    assert SECRET not in table + json.dumps(report)
    for filler in ("monday", "friday", "nine"):
        assert filler not in table + json.dumps(report)


def test_a_template_read_is_byte_stable_it_gains_no_supply_keys():
    from test_slurp_nx_solver_column_read import _read as template_read

    report = template_read()
    assert "arm_group_kind" not in report and "supply_stats" not in report


def test_a_supply_read_without_the_sealed_ids_is_refused():
    outputs, trace = _sealed()
    sealed = reader.load_sealed_arm_texts(outputs, trace)
    del sealed["supplied_ids"]["ace"]["slurp:train:4:a"]
    with pytest.raises(reader.ColumnReadError, match="no sealed supplied ids"):
        reader.read_columns(
            sealed["texts"], _gold_map(), arm_ids=sealed["arm_ids"], delivering="lock", twin="aa",
            draws=50, group_kind="supply", supplied_ids=sealed["supplied_ids"])


def test_the_two_kinds_cannot_mix_in_one_run():
    from test_slurp_nx_solver_column_read import _sealed as template_sealed

    outputs, trace = _sealed(rows=["slurp:train:1:a"])
    t_outputs, t_trace = template_sealed(rows=["slurp:train:1:b"])
    with pytest.raises(reader.ColumnReadError, match="arm group kind"):
        reader.load_sealed_arm_texts(outputs + t_outputs, {**trace, **t_trace})


def test_a_release_swap_that_differs_between_rows_is_refused():
    outputs, trace = _sealed()
    outputs[1]["supply_variants"]["arms"][1]["release_swap"] = {"store_id": "train-exemplars", "release": "knowledge/other.json"}
    with pytest.raises(reader.ColumnReadError, match="differ from the first row's"):
        reader.load_sealed_arm_texts(outputs, trace)


def test_a_knob_that_differs_between_rows_is_refused():
    outputs, trace = _sealed()
    outputs[2]["supply_variants"]["arms"][0]["resolved_knobs"] = [{"path": EX_K, "value": 11}]
    with pytest.raises(reader.ColumnReadError):
        reader.load_sealed_arm_texts(outputs, trace)


# ---------------------------------------------------------------------------
# the official column render (stage3_rollout_score --mode supply-variants)


@pytest.fixture
def _stub_delivery(monkeypatch):
    from speech_aware_evidence_acquisition.rails import native_episode_receipt

    monkeypatch.setattr(
        native_episode_receipt, "validate_native_episode_delivery_receipt",
        lambda episode, **_kw: SimpleNamespace(kind=episode["kind"]),
    )


def _bundle(tmp_path, outputs, trace):
    ids = [row["sample_id"] for row in outputs]
    for row in outputs:  # AT1: the delivered text is the delivering arm's normalised first answer
        row["text"] = score_mod.normalise_arm_answer(SUPPLY_ANSWERS["lock"][row["sample_id"]], None)[0]
    path = tmp_path / "runs" / "RUN" / "ATT" / "RUN.manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}")
    return SimpleNamespace(
        manifest={"status": "COMPLETED", "run_id": "RUN", "config": {"config_hash": "c" * 64},
                  "outputs": {"sha256": "d" * 64}, "raw_trace": {"sha256": "e" * 64},
                  "scores": {"sha256": "f" * 64}},
        attempt_state="FINALIZED", manifest_path=path, split_ids=frozenset(ids),
        outputs_rows=tuple(outputs), trace_records=trace,
    ), ids


def _render(bundle, ids, group, tmp_path):
    return score_mod.render_supply_variant_first_visit(
        bundle, group, {sid: "x" for sid in ids}, tmp_path / "analysis",
        run_id="RUN", attempt_id="ATT", roster_sha256="1" * 64, config_hash="c" * 64)


def _parsed_group(values):
    native = values["native_episode"]["roles"]
    return score_mod.parse_solver_arm_group(
        values, native["solver"], native["perception"], values["knowledge_stores"])


def test_the_official_renderer_reads_the_module_graph_supply_column(_stub_delivery, tmp_path):
    values = _values()
    group = _parsed_group(values)
    assert not group.is_template and group.arm_ids == ARMS
    assert group.arms[1].release_swap.release_relpath == ALT_RELEASE
    outputs, trace = _sealed()
    bundle, ids = _bundle(tmp_path, outputs, trace)
    manifest = _render(bundle, ids, group, tmp_path)
    assert manifest["arm_order"] == list(ARMS) and manifest["rows"] == len(GOLD)
    # all four first-visit columns, the twin and the delivering arm included, are complete
    for arm in ARMS:
        rows = list(score_mod.iter_jsonl(Path(manifest["copies"][arm]["path"])))
        assert len(rows) == len(GOLD)
    assert manifest["at1_column_reproduction_checked_rows"] == len(GOLD)
    declared = {d["arm_id"]: d for d in manifest["arm_declarations"]}
    assert declared["typ"]["resolved_knobs"] == [{"path": EX_K, "value": 10}]
    assert declared["lock"]["resolved_knobs"] == [] and declared["ace"]["max_supplied_items"] == 55


def test_the_renderer_checks_the_sealed_release_swap_against_the_declaration(_stub_delivery, tmp_path):
    group = _parsed_group(_values())
    outputs, trace = _sealed()
    outputs[0]["supply_variants"]["arms"][1]["release_swap"] = {
        "store_id": "train-exemplars", "release": "knowledge/slurp/alt/other.json"}
    bundle, ids = _bundle(tmp_path, outputs, trace)
    with pytest.raises(score_mod.Stage3ScoreError, match="release swap differs"):
        _render(bundle, ids, group, tmp_path)


def test_the_renderer_refuses_a_release_swap_arm_whose_alternate_is_not_declared():
    values = _values()
    values["knowledge_stores"]["train-exemplars"].pop("alternates")
    with pytest.raises(score_mod.Stage3ScoreError, match="absent from its declared alternates"):
        _parsed_group(values)


# ---------------------------------------------------------------------------
# the v4 applier's --column loader


def test_the_applier_loads_a_supply_arm_as_the_normalised_column(tmp_path, monkeypatch):
    import speech_aware_evidence_acquisition.core.bundle as bundle_module

    spec_ = importlib.util.spec_from_file_location(
        "slurp_nx_postproc_v4_apply", _REPO / "scripts/analysis/slurp_nx_postproc_v4_apply.py")
    apply_mod = sys.modules.get("slurp_nx_postproc_v4_apply") or importlib.util.module_from_spec(spec_)
    if "slurp_nx_postproc_v4_apply" not in sys.modules:
        sys.modules["slurp_nx_postproc_v4_apply"] = apply_mod
        spec_.loader.exec_module(apply_mod)

    outputs, trace = _sealed()
    directory = tmp_path / "runs" / "RUN" / "attempt"
    directory.mkdir(parents=True)
    (directory / "RUN.run-manifest.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(bundle_module, "verify_bundle",
                        lambda path: SimpleNamespace(outputs_rows=outputs, trace_records=trace))
    texts, block = apply_mod.column_texts(tmp_path, {"run_id": "RUN", "attempt": "attempt"}, "ace")
    assert block["kind"] == "supply-arm" and block["arm_id"] == "ace" and block["delivering_arm"] == "lock"
    assert block["arm_ids"] == list(ARMS)
    assert texts == {sid: score_mod.normalise_arm_answer(raw, None)[0]
                     for sid, raw in SUPPLY_ANSWERS["ace"].items()}
