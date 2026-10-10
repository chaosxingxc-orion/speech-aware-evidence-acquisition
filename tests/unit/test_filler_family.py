"""The rollout FILLER family (owner decision 162) is cell ROLL-2's form plus cell AGREE's agreement pins on
TRAIN Fold B rows -- and nothing else.

Config and receipt level only: no data root, no lock, no adapter, no contact. The composed-diff rule is
re-implemented here from scratch (not imported from the derivation script), so the proof does not rest on
the code it proves. Every assertion holds both before and after a chunk's readiness flip.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
from speech_aware_evidence_acquisition.core.roster import verify_roster
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash

REPO = Path(__file__).resolve().parents[2]
FAMILY_ROSTER = "docs/receipts/rosters/slurp-stage3-filler-fold-b-v1.json"
PARENT_ROSTER = "docs/receipts/rosters/slurp-evo-fold-b-v2.json"
KNOWN_OVERLAPS = "docs/receipts/filler-family-known-overlaps-2026-10-10.json"
KNOWN_OVERLAP_ROSTERS = (
    "docs/receipts/rosters/slurp-system-text-selection-400-analysis-v1.json",
    "docs/receipts/rosters/slurp-system-text-update-3-400-analysis-v1.json",
)
FOLD_A_ROSTER = "docs/receipts/rosters/slurp-evo-fold-a-v2.json"
BASE = "slurp-native-stage3-filler-fold-b-base-v1"
AGREE_ARM = "slurp-native-stage3-agree-w1-fold-a-v1"
ROLL2 = {"arm": "slurp-native-stage3-roll-2-fold-a-v1", "smoke": "slurp-native-stage3-roll-2-fold-a-smoke-4-v1"}
AGREEMENT = "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FILLER-FOLD-B-V1/agreement.jsonl"
AGREEMENT_RECEIPT = "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FILLER-FOLD-B-V1/receipt.json"
PERCEPTION = ("knowledge_stores", "intent-boundaries", "phase_supply", "perception")
SOLVER = ("knowledge_stores", "train-exemplars", "phase_supply", "solver")

AGREEMENT_PATHS = (
    "knowledge_stores.intent-boundaries.phase_supply.perception.k",
    "knowledge_stores.intent-boundaries.phase_supply.perception.rank_weights.w_agree",
    "knowledge_stores.intent-boundaries.phase_supply.perception.agreement_source.",
)
ROSTER_PATHS = (
    "knowledge_stores.intent-boundaries.phase_supply.perception.query_source.",
    "knowledge_stores.train-exemplars.phase_supply.solver.query_source.",
    "population.", "populations", "split_id", "preparation_source_receipts",
)
BOOKKEEPING_PATHS = (
    "native_contact_fit.", "prepared_phase_supply.", "cells", "experiment_id", "fragment_kind", "date", "purpose",
    "execution_plan.", "family_budget.", "generation_budget.", "what_this_is", "what_the_train_exemplars_store_is",
    "stage3_placeholders_filled", "stage3_algorithm.note", "failure_policy",
)


def _read(relpath: str) -> dict:
    return json.loads((REPO / relpath).read_text(encoding="utf-8"))


def _flatten(node, prefix: str = "") -> dict:
    out = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(_flatten(value, f"{prefix}{key}."))
    else:
        out[prefix[:-1]] = node
    return out


def _starts(path: str, prefixes: tuple) -> bool:
    for p in prefixes:
        if p.endswith("."):
            if path.startswith(p):
                return True
        elif path == p or path.startswith(p + "."):
            return True
    return False


def _composed(cell_id: str):
    cell = _read(f"configs/experiment/{cell_id}.json")["cells"][0]
    return compose(REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], cell_id)


def _get(values: dict, path: tuple):
    for key in path:
        values = values[key]
    return values


def _chunks() -> list[int]:
    family = _read(FAMILY_ROSTER)
    return sorted(int(k[1:]) for k in family["chunks"])


def _registered_chunks() -> list[int]:
    return sorted(
        k for k in _chunks()
        if (REPO / f"configs/experiment/slurp-native-stage3-filler-fold-b-c{k:02d}-v1.json").is_file()
    )


def _cells() -> list[tuple[str, str]]:
    out = []
    for k in _registered_chunks():
        if k == 1:
            out.append(("slurp-native-stage3-filler-fold-b-c01-smoke-4-v1", "smoke"))
        out.append((f"slurp-native-stage3-filler-fold-b-c{k:02d}-v1", "arm"))
    return out


# ---- the roster -------------------------------------------------------------------------------------
def test_family_roster_is_the_whole_of_train_fold_b_and_verifies() -> None:
    family = _read(FAMILY_ROSTER)
    parent = _read(PARENT_ROSTER)
    verify_roster(family)
    assert [i["sample_id"] for i in family["items"]] == [i["sample_id"] for i in parent["items"]]
    assert family["split_identity_hash"] == parent["split_identity_hash"]
    assert all(i["sample_id"].startswith("slurp:train:") for i in family["items"])


def test_chunks_partition_the_family_ten_per_scenario_and_reproduce_the_seeded_draw() -> None:
    family = _read(FAMILY_ROSTER)
    parent = _read(PARENT_ROSTER)
    rng = random.Random(family["seed"])
    by_stratum: dict[str, list] = {}
    for item in parent["items"]:
        by_stratum.setdefault(item["stratum"], []).append(item["sample_id"])
    expected: dict[int, set] = {}
    for stratum in sorted(by_stratum):
        pool = sorted(by_stratum[stratum])
        rng.shuffle(pool)
        for index in range(6):
            expected.setdefault(index + 1, set()).update(pool[index * 10:(index + 1) * 10])
    seen: list[str] = []
    for k in _chunks():
        chunk = _read(f"docs/receipts/rosters/slurp-stage3-filler-fold-b-c{k:02d}-v1.json")
        verify_roster(chunk)
        ids = [i["sample_id"] for i in chunk["items"]]
        assert set(ids) == expected[k]
        assert set(Counter(i["stratum"] for i in chunk["items"]).values()) == {10}
        assert family["chunks"][f"c{k:02d}"]["split_identity_hash"] == chunk["split_identity_hash"]
        assert chunk["split_identity_hash"] == split_identity_hash(prefixed("slurp", ids))
        seen += ids
    assert sorted(seen) == sorted(i["sample_id"] for i in family["items"]) and len(seen) == len(set(seen)) == 1080
    smoke = _read("docs/receipts/rosters/slurp-stage3-filler-fold-b-c01-smoke-4-v1.json")
    c01 = _read("docs/receipts/rosters/slurp-stage3-filler-fold-b-c01-v1.json")
    assert [i["sample_id"] for i in smoke["items"]] == [i["sample_id"] for i in c01["items"]][:4]


def test_disjointness_proof_is_complete_and_zero() -> None:
    family = _read(FAMILY_ROSTER)
    proof = family["disjointness_proof"]
    assert proof["total_shared_recordings"] == 0 and proof["total_shared_utterances"] == 0
    for relpath, entry in proof["receipts_checked"].items():
        assert entry["shared_recordings"] == 0 and entry["shared_utterances"] == 0, relpath
    for name in ("slurp-dev-2000-added-v1", "slurp-devel-remainder-v2", "slurp-test-sample-3010-v1",
                 "slurp-test-closure-10068-v1", "slurp-stage3-construction-r01c", "slurp-evo-fold-a-v2"):
        assert f"docs/receipts/rosters/{name}.json" in proof["receipts_checked"], name
    for name in ("FINAL60", "DEV-1000", "TRAIN90"):
        assert f"docs/receipts/probe-samples/{name}.json" in proof["receipts_checked"], name
    for split in ("devel", "test"):
        assert proof["governed_splits"][split]["shared_recordings"] == 0
    # re-prove against every SLURP receipt that is not the parent itself or one of its superseded draws
    mine = {i["sample_id"] for i in family["items"]}
    superseded = set(proof["superseded_never_contacted_reported_not_refused"])
    known = _read(KNOWN_OVERLAPS)["known_overlaps"]
    assert set(known) == set(KNOWN_OVERLAP_ROSTERS), "the known-overlap record names exactly two rosters"
    for rel, entry in known.items():
        assert entry["size"] == 400 and entry["shared_sample_ids_with_filler_family"] == 400, rel
        assert entry["sha256"] == hashlib.sha256((REPO / rel).read_bytes()).hexdigest(), rel
    for folder in ("docs/receipts/rosters", "docs/receipts/probe-samples"):
        for path in sorted((REPO / folder).glob("*.json")):
            rel = f"{folder}/{path.name}"
            if "filler" in rel or rel in superseded or rel in (PARENT_ROSTER, "docs/receipts/probe-samples/SLURP-EVO-FOLD-B-V2.json"):
                continue
            items = json.loads(path.read_text(encoding="utf-8")).get("items")
            ids = {i.get("sample_id") or i.get("id") for i in items if isinstance(i, dict)} if isinstance(items, list) else set()
            if rel in known:
                # Decision 243 (2026-10-10): named KNOWN CUMULATIVE EXPOSURE, asserted exactly, never zero.
                assert len(mine & ids) == known[rel]["shared_sample_ids_with_filler_family"], rel
                continue
            assert not (mine & ids), rel


def test_knowledge_guard_and_the_admissible_universe() -> None:
    guard = _read(FAMILY_ROSTER)["knowledge_source_guard"]
    assert guard["shared_recordings_with_filler"] == 0 and guard["shared_utterances_with_filler"] == 0
    for store in guard["stores"].values():
        assert store["shared_recordings_with_filler"] == 0 and store["shared_utterances_with_filler"] == 0
    universe = guard["admissible_universe"]
    assert universe["union"] == universe["slurp_train_utterances"] == 11514
    assert universe["pool_utterances"] + universe["fold_a_utterances"] + universe["fold_b_utterances"] == 11514
    fold_a = {i["utterance_id"] for i in _read(FOLD_A_ROSTER)["items"]}
    assert not fold_a & {i["utterance_id"] for i in _read(FAMILY_ROSTER)["items"]}


# ---- the composed diff against ROLL-2 ----------------------------------------------------------------
@pytest.mark.parametrize("cell_id,kind", _cells())
def test_composed_diff_against_roll2_is_exactly_agreement_pins_roster_pins_and_bookkeeping(cell_id: str, kind: str) -> None:
    mine = _composed(cell_id)
    parent = _composed(ROLL2[kind])
    dataset_keys = set(_read("configs/dataset/slurp-speech-native-evo-fold-b-1080.json"))
    a, b = _flatten(parent.values), _flatten(mine.values)
    changed = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))
    other = [
        p for p in changed
        if not (_starts(p, AGREEMENT_PATHS) or _starts(p, ROSTER_PATHS) or _starts(p, BOOKKEEPING_PATHS)
                or p.split(".", 1)[0] in dataset_keys)
    ]
    assert other == []
    assert [p for p in changed if _starts(p, AGREEMENT_PATHS)], "the agreement pins must be present"
    # everything that makes the form is ROLL-2's, byte for byte
    for key in ("native_episode", "policy", "phase_material", "scorers", "serving_slots", "serving_slot_tokens",
                "speech_packet_promotion_receipt", "speech_packet_promotion_receipt_sha256", "task_instruction_template",
                "task_instruction_fill", "arm", "evidence_source"):
        assert mine.values.get(key) == parent.values.get(key), key
    for store in ("intent-boundaries", "slot-contracts", "train-exemplars"):
        for pin in ("release", "snapshot", "store_role"):
            assert mine.values["knowledge_stores"][store][pin] == parent.values["knowledge_stores"][store][pin]
    assert mine.values["knowledge_stores"]["slot-contracts"] == parent.values["knowledge_stores"]["slot-contracts"]


@pytest.mark.parametrize("cell_id,kind", _cells())
def test_the_agreement_pins_are_agree_s_and_the_solver_moves_only_its_query(cell_id: str, kind: str) -> None:
    mine = _composed(cell_id)
    agree = _composed(AGREE_ARM)
    parent = _composed(ROLL2[kind])
    p_mine, p_agree, p_parent = (_get(v.values, PERCEPTION) for v in (mine, agree, parent))
    for key in ("k", "rank_weights", "fuse_coverage", "rank_policy", "tau", "fuse_policy", "facet_source",
                "dimensions", "provider", "expose_facets"):
        assert p_mine[key] == p_agree[key], key
    assert p_mine["k"] == 60 and p_mine["rank_weights"] == {"w_agree": 1.0, "w_cos": 1.0, "w_prior": 0.0}
    assert p_mine["fuse_coverage"] == {"c": 1, "m": 8, "top_l": 8}
    assert p_mine["agreement_source"]["relpath"] == AGREEMENT and p_mine["agreement_source"]["kind"] == "sealed-agreement"
    assert set(p_mine) - {"query_source", "k", "rank_weights", "agreement_source"} == set(p_parent) - {"query_source", "k", "rank_weights"}
    s_mine, s_parent = _get(mine.values, SOLVER), _get(parent.values, SOLVER)
    assert {k: v for k, v in s_mine.items() if k != "query_source"} == {k: v for k, v in s_parent.items() if k != "query_source"}
    assert s_mine["query_source"]["relpath"] == "vectors/slurp-stage3-filler-fold-b-v1/query-vectors-speech-content-v1.jsonl"
    assert "fold-b" in p_mine["query_source"]["relpath"]


@pytest.mark.parametrize("cell_id,kind", _cells())
def test_preparation_receipts_are_roll2_s_with_exactly_the_filler_edits(cell_id: str, kind: str) -> None:
    mine = _composed(cell_id).values["preparation_source_receipts"]
    parent = _composed(ROLL2[kind]).values["preparation_source_receipts"]
    assert len(mine) == len(parent) + 3
    for m, p in zip(mine, parent):
        if p["relpath"].endswith("TRAIN-FOLD-A-ALIAS-V1/query-dimension-alias.json"):
            assert m["relpath"] == "prepared/SAEA-SLURP-INTENT-BOUNDARY-TRAIN-FOLD-B-ALIAS-V1/query-dimension-alias.json"
        elif p["relpath"] == FOLD_A_ROSTER:
            roster = _read(f"configs/experiment/{cell_id}.json")["population"]["roster_receipt"]
            assert m["relpath"] == roster and m["root"] == "repository"
        else:
            assert m == p
    assert [m["relpath"] for m in mine[len(parent):]] == [
        "preparation-runs/SAEA-SLURP-TFRL-FOLD-B-SPEECH-QUERY-ENCODING-V1/encode-v1/receipt.json",
        "vectors/slurp-stage3-filler-fold-b-v1/query-vectors-speech-content-v1.provenance.json",
        AGREEMENT_RECEIPT,
    ]


def test_the_base_is_roll2_on_fold_b_without_the_agreement_and_is_never_flown() -> None:
    base = _composed(BASE)
    parent = _composed(ROLL2["arm"])
    p = _get(base.values, PERCEPTION)
    assert p["k"] == 8 and p["rank_weights"]["w_agree"] == 0.0 and "agreement_source" not in p
    assert _get(base.values, PERCEPTION)["query_source"] != _get(parent.values, PERCEPTION)["query_source"]
    document = _read(f"configs/experiment/{BASE}.json")
    cell = document["cells"][0]
    assert cell["allowed_execution_stages"] == ["check"]
    assert cell["readiness"]["state"] == "held" and cell["readiness"]["requirements"] == []
    assert document["stage3_algorithm"]["id"] == "none"
    assert not (REPO / f"configs/campaign/{BASE}.json").exists()
    assert base.values["native_episode"] == parent.values["native_episode"]
    ledger = (REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    assert "| SAEA-SLURP-STAGE3-FILLER-FOLD-B-BASE-V1 |" not in ledger


# ---- registration bookkeeping ------------------------------------------------------------------------
@pytest.mark.parametrize("cell_id,kind", _cells())
def test_population_budgets_readiness_and_label(cell_id: str, kind: str) -> None:
    document = _read(f"configs/experiment/{cell_id}.json")
    roster = _read(document["population"]["roster_receipt"])
    ids = [i["sample_id"] for i in roster["items"]]
    rows = len(ids)
    assert document["populations"][0]["ids"] == ids
    assert document["population"]["count"] == rows
    assert document["population"]["split_identity_hash"] == roster["split_identity_hash"]
    assert document["split_id"] == "SLURP-EVO-FOLD-B-V2"  # the Fold B runtime view's split_name
    budget = document["family_budget"]
    assert budget["generation_calls_cap"] == rows * 19 == document["execution_plan"]["planned_model_calls"]
    assert budget["fit_endpoint_calls_cap"] == rows * 19 * 4
    speech = math.ceil(sum(float(i["audio_seconds"]) for i in roster["items"]) * 19)
    assert abs(budget["repeated_speech_audio_seconds_cap"] - speech) <= 1
    assert budget["gpu_hours_fit_inclusive"] == (1.0 if kind == "smoke" else round(12.0 * rows / 1080, 4))
    assert budget["native_task_contract_calls_cap"] == 0
    assert budget["official_complete_scoring_jobs"] == (0 if kind == "smoke" else 1)
    baseline = _read(f"configs/baseline/{document['cells'][0]['baseline_fragment']}.json")
    assert baseline["native_contact_fit"]["contact_cap"] == rows * 19 * 4
    assert baseline["native_episode"]["finite_completion_policy"] == "deliver-latest-or-abstain"
    assert baseline["native_episode"]["react_exhaustion_policy"] == "continue-without-answer"
    assert document["stage3_algorithm"]["id"] == "shared-rollout"
    assert document["stage3_algorithm"]["operators_used"] == ["rollout"]
    readiness = document["cells"][0]["readiness"]
    assert readiness["state"] in ("held", "ready")
    agreement = [r for r in readiness["requirements"] if r.get("relpath") == AGREEMENT]
    assert len(agreement) == 1 and agreement[0]["kind"] == "preparation"
    if readiness["state"] == "held":
        assert readiness["requirements"] == agreement


@pytest.mark.parametrize("k", _registered_chunks())
def test_the_package_pins_the_composed_identity_and_declares_a_descriptive_pool(k: int) -> None:
    package = f"docs/readiness/2026-09-27-slurp-stage3-filler-fold-b-c{k:02d}-v1"
    facts = _read(f"{package}/registered-facts-v1.json")
    cells = [c for c in _cells() if f"-c{k:02d}-" in c[0]]
    for cell_id, kind in cells:
        document = _read(f"configs/experiment/{cell_id}.json")
        run = document["cells"][0]["run_id"]
        block = facts["stage3_measurement"][run]
        assert block["claims_benefit"] is False and block["expected_effect_pp"] == 0.0
        assert block["measurement_design"] == ("form-proof" if kind == "smoke" else "offline-sealed-pool")
        prefix = "smoke-generation" if kind == "smoke" else "generation"
        plan = _read(f"{package}/{prefix}-plan-registered-v1.json")
        composed = _composed(cell_id)
        assert plan["composed_config_hash"] == composed.config_hash
        assert plan["execution_plan"]["protocol_hash"] == protocol_hash(
            composed.config_hash, composed.values["arm"], document["population"]["split_identity_hash"])
        assert plan["execution_plan"]["run_id"] == run
    step = _read(f"{package}/queue-step-v1.json")
    assert step["run_id"] == f"SAEA-SLURP-STAGE3-FILLER-FOLD-B-C{k:02d}-V1"
    assert step["campaign_plan"] == f"configs/campaign/slurp-native-stage3-filler-fold-b-c{k:02d}-v1.json"
    assert (step["smoke_cell"] is not None) == (k == 1)
    campaign = _read(step["campaign_plan"])
    assert campaign["cells"] == [{"cell": step["cell"], "experiment": step["cell"]}]
    draft = _read(f"{package}/root-admission-draft-v1.json")
    assert draft["decision_id"] == f"slurp-stage3-filler-fold-b-c{k:02d}-admission-v1"
    assert draft["status"] == "DRAFT-NOT-MINTED"
    assert step["run_id"] in draft["eligible_run_ids"] and step["fit_run_id"] in draft["eligible_run_ids"]


def test_every_registered_run_id_has_exactly_one_ledger_row_without_a_pipe_in_any_cell() -> None:
    ledger = (REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8").split("\n")
    for k in _registered_chunks():
        runs = [f"SAEA-SLURP-STAGE3-FILLER-FOLD-B-C{k:02d}-V1", f"SAEA-SLURP-STAGE3-FILLER-FOLD-B-C{k:02d}-FIT-V1"]
        if k == 1:
            runs += ["SAEA-SLURP-STAGE3-FILLER-FOLD-B-C01-SMOKE-4-V1", "SAEA-SLURP-STAGE3-FILLER-FOLD-B-C01-SMOKE-4-FIT-V1"]
        for run in runs + ["SAEA-SLURP-STAGE3-FILLER-FOLD-B-PREPARE-V1"]:
            rows = [line for line in ledger if line.startswith("|") and line.split("|")[2].strip() == run]
            assert len(rows) == 1, run
            assert len(rows[0].split("|")) == 17, run  # fifteen cells: no literal '|' inside any cell
