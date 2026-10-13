"""Tests of ``scripts/flights/tfrl/tfrl_cell_stage_inputs.py``: the model-free extractor of the ``open --stage cell`` input set.

Synthetic worlds exercise the builders, the write-once / supersede discipline and the execute path (the preparer is replaced by a stub that
writes the three canonical release files); the iteration-1 regression runs the real tool against the live iteration-1 artefacts when the data
root is present and skips cleanly otherwise. No test prints or asserts on utterance text, transcripts or gold labels.
"""

from __future__ import annotations

import os
import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TFRL = REPO / "scripts" / "flights" / "tfrl"
for _p in (str(REPO / "src"), str(TFRL)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import tfrl_cell_stage_inputs as tool  # noqa: E402
import tfrl_family as tf  # noqa: E402
import tfrl_loop_driver as drv  # noqa: E402
import tfrl_loop_lib as lib  # noqa: E402
import tfrl_overlay  # noqa: E402

from speech_aware_evidence_acquisition.rails import tfrl_ace_material as ace  # noqa: E402
from speech_aware_evidence_acquisition.rails import tfrl_typed_proposer as tp  # noqa: E402

REAL_DATA = Path((os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"))
SLOT_TYPES = ["date", "time", "place_name"]
INTENTS = sorted({f"{s}_query" for s in tp.SCENARIOS} | {"alarm_set"})


def delivery_candidate(intent: str = "alarm_query") -> dict:
    return {"schema": tp.CANDIDATE_SCHEMA_ID, "iteration": 1, "parent_state_id": drv.ROOT_DISPLAY, "operator_class": "delivery",
            "operator": "deliver-rule", "hypothesis_code": "rule-filter",
            "target": {"failure_class": "SPURIOUS", "scenarios": ["alarm"], "slot_types": ["time"], "value_in_supply": "none"},
            "applications": [{"family": "fx-oclock", "guard": "none", "intents": [intent], "types": ["time"]}]}


def reflector_text(scenario: str, n: int = 1) -> str:
    return json.dumps({"deltas": [{"op": "add", "target_id": "", "section": "strategy", "scope": {"scenarios": [scenario], "slot_types": []},
                                   "text": f"Alpha {scenario} beta{i} gamma{i} delta{i} epsilon{i} zeta{i} eta{i} theta{i}.",
                                   "rationale": "boundary errors dominate"} for i in range(n)]})


def row(sample_id: str, text: str, tag: str) -> dict:
    return {"sample_id": sample_id, "text": text, "response_sha256": hashlib.sha256(tag.encode()).hexdigest(), "admitted": True}


# ---------------------------------------------------------------------------------------------------------------------------
# pure builders
# ---------------------------------------------------------------------------------------------------------------------------


def test_typed_receipts_keep_the_i1_list_shape_and_count_refusals_by_code():
    source = {"rows": [row("a", json.dumps(delivery_candidate()), "1"), row("b", json.dumps(delivery_candidate()), "2"),
                       row("c", "not json at all", "3")]}
    entries, counts = tool.build_typed_receipts(source)
    assert isinstance(entries, list) and [sorted(e) for e in entries] == [["receipt", "response_sha256_prefix", "sample_id_sha_prefix"]] * 3
    assert entries[0]["response_sha256_prefix"] == hashlib.sha256(b"1").hexdigest()[:12]
    assert entries[0]["sample_id_sha_prefix"] == hashlib.sha256(b"a").hexdigest()[:12]
    assert counts == {"contacts": 3, "schema_valid": 2, "schema_refused": 1, "refusal_codes": {"not-json": 1}, "distinct_candidates": 1,
                      "by_class_operator": {"delivery/deliver-rule": 2}}


def test_predictions_cover_only_the_classes_named_and_count_the_missing_ones():
    supply = {"schema": tp.CANDIDATE_SCHEMA_ID, "iteration": 1, "parent_state_id": drv.ROOT_DISPLAY, "operator_class": "supply",
              "operator": "knob-set", "hypothesis_code": "type-inventory",
              "target": {"failure_class": "MISSING", "slot_types": ["date"], "scenarios": ["calendar"], "value_in_supply": "E1"},
              "applications": [{"tail": "train-exemplars.phase_supply.solver.k", "value": 12}]}
    entries, _ = tool.build_typed_receipts({"rows": [row("a", json.dumps(supply), "1"), row("b", json.dumps(delivery_candidate()), "2")]})
    empty, counts = tool.build_predictions(entries, None)
    assert empty == {"schema": tool.PREDICTIONS_SCHEMA, "predictions": {}}
    assert counts == {"predictions": 0, "predicted_class_candidates": 1, "prediction_missing": 1}
    named, counts = tool.build_predictions(entries, {"supply": {"slu_pp": -0.5, "basis": "class table"}})
    assert list(named["predictions"].values()) == [{"slu_pp": -0.5, "basis": "class table"}]
    assert counts["prediction_missing"] == 0
    cid = entries[0]["receipt"]["candidate_id"]
    assert cid in named["predictions"]


def roster_source(strata: dict[str, list[str]], rows: list[dict]) -> dict:
    items = [{"sample_id": sid, "stratum": scn} for scn, sids in strata.items() for sid in sids]
    return {"rows": rows, "roster": {"items": items}, "roster_relpath": "docs/receipts/rosters/x.json", "run_id": "RUN-X"}


def test_the_reflector_answer_per_scenario_is_the_first_non_empty_and_the_dedupe_is_recorded_by_hash_prefix_only():
    source = roster_source({"alarm": ["a1", "a2", "a3"], "audio": ["u1", "u2"]}, [
        row("a1", reflector_text("alarm", 2), "A1"), row("a2", reflector_text("alarm", 1), "A2"), row("a3", reflector_text("alarm", 0), "A3"),
        row("u1", reflector_text("audio", 0), "U1"), row("u2", reflector_text("audio", 3), "U2")])
    doc, counts, extra = tool.build_reflector_answers(source, 2)
    assert sorted(doc["answers"]) == ["alarm", "audio"]
    assert len(json.loads(doc["answers"]["alarm"])["deltas"]) == 2 and len(json.loads(doc["answers"]["audio"])["deltas"]) == 3
    assert doc["dropped_duplicates"] == [{"scenario": "alarm", "response_sha256_prefix": hashlib.sha256(b"A2").hexdigest()[:10], "deltas": 1},
                                         {"scenario": "alarm", "response_sha256_prefix": hashlib.sha256(b"A3").hexdigest()[:10], "deltas": 0}]
    # an empty first answer replaced by a later non-empty one is recorded in the provenance extra, not in the i1-shaped document
    assert extra["replaced_empty_answers"] == [{"scenario": "audio", "response_sha256_prefix": hashlib.sha256(b"U1").hexdigest()[:10], "deltas": 0}]
    assert counts["parsed"] == 5 and counts["rejected"] == 0 and counts["scenarios"] == 2 and counts["deltas_in_kept_answers"] == 5
    assert set(doc) == {"schema", "run_id", "mapping", "dropped_duplicates", "answers"}


def test_a_reflector_contact_outside_the_roster_is_refused_and_an_illegal_answer_is_counted_by_error_class_only():
    with pytest.raises(tool.ToolError):
        tool.build_reflector_answers(roster_source({"alarm": ["a1"]}, [row("zz", reflector_text("alarm"), "Z")]), 2)
    doc, counts, _ = tool.build_reflector_answers(roster_source({"alarm": ["a1"]}, [row("a1", "{\"deltas\": [{\"op\": \"explode\"}]}", "B")]), 2)
    assert counts["rejected"] == 1 and sum(counts["rejected_codes"].values()) == 1 and list(doc["answers"]) == ["alarm"]


def test_dumps_matches_the_hand_script_serialisation_and_compare_names_the_differing_fields():
    assert tool.dumps({"b": 1, "a": [1]}) == b'{\n "a": [\n  1\n ],\n "b": 1\n}'
    assert tool.dumps({"b": 1, "a": 2}, sort_keys=False).startswith(b'{\n "b": 1')
    fresh = tool.dumps({"a": 1, "b": 2})
    assert tool.compare(None, fresh) == {"state": "new"}
    assert tool.compare(fresh, fresh) == {"state": "identical"}
    assert tool.compare(tool.dumps({"a": 1, "b": 2, "provenance": {"tool": "old"}}), fresh)["state"] == "stable-match"
    assert tool.compare(tool.dumps({"a": 1, "b": 3}), fresh) == {"state": "differs", "fields": ["b"]}
    assert tool.compare(b"{ \"a\": 1,  \"b\": 2 }", fresh)["state"] == "identical-semantics"


def test_pins_carry_the_preparers_content_hashes_not_file_hashes():
    completion = {"release": {"relpath": "knowledge/x/release.json", "sha256": "r" * 64}, "snapshot": {"relpath": "knowledge/x/snapshot.json", "sha256": "c" * 64},
                  "snapshot_file_sha256": "f" * 64}
    pins = tool.pins_doc(2, completion, "docs/x/registration.json")
    assert pins["snapshot_sha256"] == "c" * 64 and pins["snapshot_file_sha256"] == "f" * 64 and pins["release_sha256"] == "r" * 64
    assert set(pins) == {"release_relpath", "release_sha256", "snapshot_relpath", "snapshot_sha256", "snapshot_file_sha256", "prepared_by"}


# ---------------------------------------------------------------------------------------------------------------------------
# a synthetic world: sealed outputs, a copied package, a stubbed preparer
# ---------------------------------------------------------------------------------------------------------------------------


class World:
    def __init__(self, tmp_path: Path, monkeypatch):
        self.root = tfrl_overlay.make_overlay(tmp_path / "overlay", REPO)
        self.pkg = self.root / tf.PACKAGE_DIR
        self.data = tmp_path / "data"
        self.t = 1
        self.A = self.data / tf.ANALYSIS_ROOT / "i1"
        self.prepared: list[Path] = []
        registration = json.loads((REPO / lib.ACE_I0_REGISTRATION_RELPATH).read_text(encoding="utf-8"))
        for key, source in (("construction_scope", tf.CONST_ROSTER["arm"]), ("permitted_roster", lib.ACE_CARRIER_ROSTER_RELPATH)):
            target = self.data / registration[key]["relpath"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((REPO / source).read_bytes())
        (self.pkg / "ace-playbook-i1-release-registration.json").unlink()      # the overlay copies the live registration; the world starts without it
        # the propose stage's artefacts
        (self.A / "playbook").mkdir(parents=True)
        ace.write_playbook(self.A / "playbook" / "playbook-i0.json", ace.empty_playbook())
        (self.A / "proposer-tables.json").write_text(json.dumps({"enums": {"slot_types": SLOT_TYPES, "intents": INTENTS, "scenarios": list(tp.SCENARIOS)}}),
                                                     encoding="utf-8")
        self.seal_typed([json.dumps(delivery_candidate()), json.dumps(delivery_candidate()), "garbage"])
        self.seal_reflector()
        monkeypatch.setattr(tool, "prepare_in", self.fake_prepare)

    def seal(self, kind: str, rows: list[dict]) -> None:
        names = tf.names(self.t, kind)
        target = self.data / "runs" / names["run_id"] / names["attempt_id"] / f"{names['run_id']}.outputs.jsonl"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    def seal_typed(self, texts: list[str]) -> None:
        roster = json.loads((self.root / tf.names(self.t, "typed")["carrier_roster"]).read_text(encoding="utf-8"))["items"]
        self.seal("typed", [row(roster[i % len(roster)]["sample_id"], text, f"T{i}{text[:8]}") for i, text in enumerate(texts)])

    def seal_reflector(self, n_deltas: int = 1) -> None:
        roster = json.loads((self.root / tf.names(self.t, "ace")["carrier_roster"]).read_text(encoding="utf-8"))["items"]
        self.seal("ace", [row(item["sample_id"], reflector_text(item["stratum"], n_deltas), f"R{i}{n_deltas}") for i, item in enumerate(roster)])

    def fake_prepare(self, data_root: Path, repo_root: Path, registration: Path):
        """Stand-in for the preparer: three canonical release files whose content hashes derive from the registration bytes."""

        digest = hashlib.sha256(Path(registration).read_bytes()).hexdigest()
        namespace = Path(data_root) / "knowledge" / "slurp" / "semantic" / f"ace-playbook-i{self.t}"
        namespace.mkdir(parents=True, exist_ok=True)
        snapshot = tool.dumps({"stub": digest})
        release = tool.dumps({"snapshot_sha256": digest})
        completion = tool.dumps({"release": {"relpath": f"knowledge/slurp/semantic/ace-playbook-i{self.t}/release.json", "sha256": hashlib.sha256(release).hexdigest()},
                                 "snapshot": {"relpath": f"knowledge/slurp/semantic/ace-playbook-i{self.t}/snapshot.json", "sha256": digest},
                                 "snapshot_file_sha256": hashlib.sha256(snapshot).hexdigest()})
        for name, raw in (("snapshot.json", snapshot), ("release.json", release), ("completion.json", completion)):
            (namespace / name).write_bytes(raw)
        self.prepared.append(Path(data_root))
        return {}

    def args(self, *extra: str) -> list[str]:
        return ["--iter", str(self.t), "--repo-root", str(self.root), "--data-root", str(self.data), *extra]


@pytest.fixture()
def world(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def run_tool(world: World, *extra: str) -> tuple[int, str]:
    out: list[str] = []
    code = tool.main(world.args(*extra), out=out.append)
    return code, "\n".join(out)


def test_a_dry_run_writes_nothing_under_the_data_root_or_the_package_and_reports_hashes(world):
    before = sorted(p.relative_to(world.data).as_posix() for p in world.data.rglob("*") if p.is_file())
    pkg_before = sorted(p.name for p in world.pkg.iterdir())
    code, text = run_tool(world)
    assert code == 0
    report = json.loads(text)
    assert report["mode"] == "dry-run" and report["tool"] == tool.TOOL_VERSION and report["iteration"] == 1
    assert sorted(p.relative_to(world.data).as_posix() for p in world.data.rglob("*") if p.is_file()) == before
    assert sorted(p.name for p in world.pkg.iterdir()) == pkg_before
    names = [a["name"] for a in report["artefacts"]]
    assert {"typed-receipts-i1.json", "predictions-i1.json", "reflector-answers-i1.json", "enums-i1.json"} <= set(names)
    assert "ace-release-pins-i1.json" not in names                               # the registration is not in the repository yet: the preparer is deferred
    assert report["counts"]["typed"]["schema_valid"] == 2 and report["counts"]["typed"]["refusal_codes"] == {"not-json": 1}
    assert report["counts"]["playbook"]["items_before"] == 0 and report["counts"]["playbook"]["items_after"] > 0
    assert report["sources"]["typed"]["outputs_sha256"] and report["sources"]["ace"]["run_id"] == tf.names(1, "ace")["run_id"]


def test_execute_writes_the_input_set_once_and_a_rerun_is_a_no_op(world):
    code, text = run_tool(world, "--execute")
    assert code == 0, text
    report = json.loads(text)
    assert report["mode"] == "execute"
    # ruling 300 A: the sealed i1 typed receipts are the OLD layout (response-hash prefix in sample_id_sha_prefix, no offered classes). They stay
    # readable and labelled; the fresh build is the new layout, so the comparison reports a difference by design.
    assert states["typed-receipts-i1.json"] == {"state": "differs", "fields": ["<document>"]}
    live_entries = json.loads((REAL_DATA / tf.ANALYSIS_ROOT / "i1" / "typed-receipts-i1.json").read_text(encoding="utf-8"))
    assert {lib.typed_entry_layout(e) for e in live_entries} == {lib.TYPED_ENTRY_LAYOUT_V1}
    assert all(lib.typed_entry_response_prefix(e) == e["sample_id_sha_prefix"] for e in live_entries)
    for name in ("predictions-i1.json", "reflector-answers-i1.json", "enums-i1.json", "ace-release-pins-i1.json",
                 "ace-i1-release-files.json", "cell-stage-inputs-i1.json"):
        assert (world.A / name).is_file(), name
    assert (world.A / "ace-release-staging" / "playbook-i1.json").is_file()
    assert (world.pkg / "ace-playbook-i1-release-registration.json").is_file()
    namespace = world.data / "knowledge" / "slurp" / "semantic" / "ace-playbook-i1"
    assert sorted(p.name for p in namespace.iterdir()) == ["completion.json", "release.json", "snapshot.json"]
    pins = json.loads((world.A / "ace-release-pins-i1.json").read_text(encoding="utf-8"))
    completion = json.loads((namespace / "completion.json").read_text(encoding="utf-8"))
    assert pins["snapshot_sha256"] == completion["snapshot"]["sha256"] != pins["snapshot_file_sha256"]
    assert pins["release_sha256"] == hashlib.sha256((namespace / "release.json").read_bytes()).hexdigest()
    assert pins["provenance"]["tool"] == tool.TOOL_VERSION
    # the dict artefacts carry schema, iteration, source run and attempt ids and the sealed outputs digest in their provenance
    answers = json.loads((world.A / "reflector-answers-i1.json").read_text(encoding="utf-8"))
    assert answers["provenance"]["source"]["attempt_id"] == tf.names(1, "ace")["attempt_id"] and answers["provenance"]["source"]["outputs_sha256"]
    assert answers["schema"] == tool.ANSWERS_SCHEMA
    manifest = json.loads((world.A / "cell-stage-inputs-i1.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == tool.MANIFEST_SCHEMA and manifest["sources"]["typed"]["outputs_sha256"]
    # the receipts file keeps the driver's list shape
    assert isinstance(json.loads((world.A / "typed-receipts-i1.json").read_text(encoding="utf-8")), list)
    # a rerun changes nothing (write-once; the installed states are unchanged)
    before = {p: p.read_bytes() for p in world.data.rglob("*") if p.is_file()}
    code, text = run_tool(world, "--execute")
    assert code == 0, text
    assert {p: p.read_bytes() for p in world.data.rglob("*") if p.is_file()} == before
    assert all(a.get("installed") in ("unchanged", None) for a in json.loads(text)["artefacts"])


def test_the_driver_accepts_the_produced_pins_and_enums_files(world):
    assert run_tool(world, "--execute")[0] == 0
    assert drv.read_or_none(world.A / "ace-release-pins-i1.json")["snapshot_sha256"]
    enums = json.loads((world.A / "enums-i1.json").read_text(encoding="utf-8"))
    assert list(enums)[:2] == ["schema", "source"] and enums["intents"] == INTENTS


def test_a_changed_sealed_input_is_refused_unless_superseded_and_the_old_bytes_are_kept(world):
    assert run_tool(world, "--execute")[0] == 0
    old = (world.A / "reflector-answers-i1.json").read_bytes()
    world.seal_reflector(n_deltas=2)                                  # different sealed outputs
    code, text = run_tool(world, "--execute")
    assert code == 3 and "write-once" in text
    assert (world.A / "reflector-answers-i1.json").read_bytes() == old
    code, text = run_tool(world, "--execute", "--supersede")
    assert code == 0, text
    kept = sorted(p.name for p in world.A.glob("reflector-answers-i1.superseded-*.json"))
    assert len(kept) == 1 and (world.A / kept[0]).read_bytes() == old
    assert (world.A / "reflector-answers-i1.json").read_bytes() != old


def test_a_missing_sealed_output_or_propose_receipt_stops_the_tool_by_name(world):
    names = tf.names(1, "ace")
    (world.data / "runs" / names["run_id"] / names["attempt_id"] / f"{names['run_id']}.outputs.jsonl").unlink()
    code, text = run_tool(world)
    assert code == 3 and "sealed ace outputs are missing" in text


def test_no_provenance_gives_the_exact_hand_script_shape(world):
    code, text = run_tool(world, "--no-provenance")
    assert code == 0
    report = json.loads(text)
    by = {a["name"]: a for a in report["artefacts"]}
    assert all(a["sha256"] == a["core_sha256"] for a in report["artefacts"])
    assert by["enums-i1.json"]["sha256"] == by["enums-i1.json"]["core_sha256"]


# ---------------------------------------------------------------------------------------------------------------------------
# regression against the live iteration-1 artefacts
# ---------------------------------------------------------------------------------------------------------------------------

I1_OUTPUTS = REAL_DATA / "runs" / "SAEA-SLURP-STAGE3-TFRL-PROPOSER-I1-V1"


@pytest.mark.skipif(not (I1_OUTPUTS.is_dir() and (REAL_DATA / tf.ANALYSIS_ROOT / "i1" / "typed-receipts-i1.json").is_file()),
                    reason="the live data root with the iteration-1 artefacts is not present")
def test_iteration_one_regression_reproduces_the_hand_built_inputs_byte_for_byte_except_the_pins_free_text(tmp_path):
    out: list[str] = []
    code = tool.main(["--iter", "1", "--data-root", str(REAL_DATA), "--repo-root", str(REPO)], out=out.append)
    assert code == 0
    report = json.loads("\n".join(out))
    assert report["mode"] == "dry-run"
    states = {a["name"].split("/")[-1]: a["vs_existing"] for a in report["artefacts"]}
    for name in ("predictions-i1.json", "reflector-answers-i1.json", "enums-i1.json", "authored-ace-playbook-i1.json",
                 "playbook-i1.json", "source-ace-playbook-i1.json", "source-ace-playbook-i1-wrap-receipt.json",
                 "ace-playbook-i1-release-registration.json", "release.json", "snapshot.json", "completion.json", "ace-i1-release-files.json"):
        assert states[name] == {"state": "identical"}, name
    # the pins differ only in the hand script's free-text annotation
    assert states["ace-release-pins-i1.json"] == {"state": "differs", "fields": ["prepared_by"]}
    live = json.loads((REAL_DATA / tf.ANALYSIS_ROOT / "i1" / "ace-release-pins-i1.json").read_text(encoding="utf-8"))
    for key in ("release_relpath", "release_sha256", "snapshot_relpath", "snapshot_sha256", "snapshot_file_sha256"):
        assert report["pins"][key] == live[key], key
    assert report["counts"]["playbook"]["content_hash"] == "e12fabcc1a8c72c93a2b0b5ceb14ba1d1168c93ac8ba4fbcc05ab5af4820e28e"


# ---------------------------------------------------------------------------------------------------------------------------
# owner ruling 300 A: the offered class set and the two hash prefixes
# ---------------------------------------------------------------------------------------------------------------------------


def test_v2_entries_hold_the_sample_id_sha_the_response_sha_and_the_offered_classes_and_count_the_class_violations():
    source = {"offered_classes": {"a": ["supply"], "b": ["delivery", "scope"], "c": ["construction"]},
              "rows": [row("a", json.dumps(delivery_candidate()), "1"), row("b", json.dumps(delivery_candidate()), "2"),
                       row("c", "not json at all", "3")]}
    entries, counts = tool.build_typed_receipts(source)
    assert [sorted(e) for e in entries] == [["allowed_classes", "receipt", "response_sha256_prefix", "sample_id_sha_prefix"]] * 3
    assert entries[0]["sample_id_sha_prefix"] == hashlib.sha256(b"a").hexdigest()[:12]
    assert entries[0]["response_sha256_prefix"] == hashlib.sha256(b"1").hexdigest()[:12]
    assert entries[0]["sample_id_sha_prefix"] != entries[0]["response_sha256_prefix"]
    assert [e["allowed_classes"] for e in entries] == [["supply"], ["delivery", "scope"], ["construction"]]
    assert all(lib.typed_entry_layout(e) == lib.TYPED_ENTRY_LAYOUT_V2 for e in entries)
    assert counts["class_not_offered"] == 1                       # the delivery candidate of carrier "a", offered only supply


def test_a_contact_missing_from_the_proposer_brief_stops_the_extractor_instead_of_dropping_the_class_check():
    with pytest.raises(tool.ToolError):
        tool.build_typed_receipts({"offered_classes": {"a": ["supply"]}, "rows": [row("zz", json.dumps(delivery_candidate()), "1")]})


def test_both_entry_layouts_are_readable_and_the_old_one_is_labelled():
    legacy = {"receipt": {"response_sha256": hashlib.sha256(b"1").hexdigest()}, "sample_id_sha_prefix": hashlib.sha256(b"1").hexdigest()[:12]}
    entries, _ = tool.build_typed_receipts({"offered_classes": {"a": ["supply"]}, "rows": [row("a", json.dumps(delivery_candidate()), "1")]})
    assert lib.typed_entry_layout(legacy) == lib.TYPED_ENTRY_LAYOUT_V1 and lib.typed_entry_layout(entries[0]) == lib.TYPED_ENTRY_LAYOUT_V2
    assert lib.typed_entry_response_prefix(legacy) == lib.typed_entry_response_prefix(entries[0]) == hashlib.sha256(b"1").hexdigest()[:12]
    assert lib.typed_entry_sample_id_prefix(legacy) is None
    assert lib.typed_entry_sample_id_prefix(entries[0]) == hashlib.sha256(b"a").hexdigest()[:12]


def test_the_offered_classes_are_read_from_the_registered_proposer_brief(tmp_path):
    names = tf.names(1, "typed")
    brief = tmp_path / "configs" / "baseline" / f"{names['baseline']}.json"
    brief.parent.mkdir(parents=True)
    brief.write_text(json.dumps({"tfrl_proposer": {"carriers": [{"sample_id": "a", "allowed_classes": ["supply"]},
                                                                {"sample_id": "b", "allowed_classes": ["delivery", "scope"]}]}}), encoding="utf-8")
    assert tool.offered_classes(tmp_path, names) == {"a": ["supply"], "b": ["delivery", "scope"]}
    brief.write_text(json.dumps({"tfrl_proposer": {"carriers": [{"sample_id": "a"}]}}), encoding="utf-8")
    with pytest.raises(lib.MissingInput):
        tool.offered_classes(tmp_path, names)
    brief.unlink()
    with pytest.raises(lib.MissingInput):
        tool.offered_classes(tmp_path, names)
