"""Pinned successor identities preserve real configuration and legacy admission."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import pytest
from speech_aware_evidence_acquisition.rails import architecture_natural_registration as admission
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
ROOT = Path(__file__).resolve().parents[2]


def write(root, rel, value):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    return {"relpath": rel, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}


def fixture(tmp_path):
    root = tmp_path / "repo"
    shutil.copytree(ROOT / "configs", root / "configs")
    pop_rel = "configs/experiments/slurp-simple-consumption-architecture-n100-v1.json"
    population = json.loads((root / pop_rel).read_bytes())
    pop_pin = {"relpath": pop_rel, "sha256": hashlib.sha256((root / pop_rel).read_bytes()).hexdigest()}
    members = []
    for m in population["architecture"]["members"]:
        label = m["member_id"]
        old = "slurp-native-stage3-simple-consumption-" + label + "-n100-v1"
        new = old.removesuffix("-v1") + "-audio-recovery1-v1"
        ep_rel, bp_rel = "configs/experiment/" + old + ".json", "configs/baseline/" + old + ".json"
        ep, bp = json.loads((root / ep_rel).read_bytes()), json.loads((root / bp_rel).read_bytes())
        def pin(rel):
            return {"relpath": rel, "sha256": hashlib.sha256((root / rel).read_bytes()).hexdigest()}
        c = ep["cells"][0]
        run = c["run_id"].removesuffix("-V1") + "-AUDIO-RECOVERY1-V1"
        attempt = "attempt-" + new + "-generation"
        audio = 3820 if m["model_per_trajectory"] == 13 else ep["execution_plan"]["planned_speech_audio_seconds"]
        row = dict(member_id=label, experiment=new, cell_id=new, run_id=run, attempt_id=attempt,
                   fit_run_id=run.removesuffix("-V1") + "-FIT-V1", fit_attempt_id=attempt + "-fit",
                   planned_speech_audio_seconds=audio, predecessor_experiment=pin(ep_rel), predecessor_baseline=pin(bp_rel))
        ep["experiment_id"] = run
        ep["execution_plan"]["planned_speech_audio_seconds"] = audio
        c.update(cell_id=new, run_id=run, attempt_id=attempt, baseline_fragment=new,
                 readiness={"state": "held", "reason": "Prospective audio recovery", "requirements": []})
        bp["native_contact_fit"].update(run_id=row["fit_run_id"], attempt_id=row["fit_attempt_id"])
        write(root, "configs/experiment/" + new + ".json", ep)
        write(root, "configs/baseline/" + new + ".json", bp)
        members.append(row)
    extent = bp["architecture_extent"]
    mapping = dict(schema="saea-manual-architecture-execution-identity-map-v1",
                   experiment_population=pop_pin, architecture_extent=extent, members=members)
    return root, population, pop_pin, extent, mapping


def checked(root, population, pop_pin, extent, mapping):
    pin = write(root, "docs/readiness/identity-map.json", mapping)
    return admission._mapped_execution_cells(pin, population, pop_pin, extent, repo_root=root)


def test_real_four_successors_compose_without_final_config_self_pin(tmp_path):
    root, population, pin, extent, mapping = fixture(tmp_path)
    cells = checked(root, population, pin, extent, mapping)
    assert [row[0] for row in cells] == [m["member_id"] for m in population["architecture"]["members"]]
    assert len({run for _, cell, c in cells for run in (cell.document["run_id"], c.values["native_contact_fit"]["run_id"])}) == 8


@pytest.mark.parametrize("mutation", ["swapped", "duplicate", "foreign", "old-run", "duplicate-attempt", "raw-predecessor", "audio", "gpu", "dataset", "policy", "roster", "cell"])
def test_identity_or_unrelated_config_changes_refused(tmp_path, mutation):
    root, population, pin, extent, mapping = fixture(tmp_path)
    row = mapping["members"][0]
    if mutation == "swapped": mapping["members"] = list(reversed(mapping["members"]))
    elif mutation == "duplicate": mapping["members"][1] = deepcopy(row)
    elif mutation == "foreign": row["member_id"] = "foreign"
    elif mutation == "old-run": row["run_id"] = json.loads((root / row["predecessor_experiment"]["relpath"]).read_bytes())["cells"][0]["run_id"]
    elif mutation == "duplicate-attempt": mapping["members"][1]["attempt_id"] = row["attempt_id"]
    elif mutation == "raw-predecessor": row["predecessor_experiment"]["sha256"] = "a" * 64
    else:
        rel = "configs/experiment/" + row["experiment"] + ".json"
        ep = json.loads((root / rel).read_bytes())
        if mutation == "audio": ep["execution_plan"]["planned_speech_audio_seconds"] += 1
        elif mutation == "gpu": ep["execution_plan"]["planned_gpu_hours"] += 1
        elif mutation == "dataset": ep["cells"][0]["dataset_fragment"] += "-foreign"
        elif mutation == "cell": ep["cells"][0]["run_id"] += "-foreign"
        elif mutation == "roster": ep["populations"][0]["ids"].reverse()
        elif mutation == "policy":
            rel = "configs/baseline/" + row["experiment"] + ".json"
            ep = json.loads((root / rel).read_bytes()); ep["evidence_source"] = "foreign"
        write(root, rel, ep)
    with pytest.raises((PolicyError, ValueError, FileNotFoundError)):
        checked(root, population, pin, extent, mapping)


def test_admission_metadata_can_change_without_map_cycle(tmp_path):
    root, population, pin, extent, mapping = fixture(tmp_path)
    for row in mapping["members"]:
        rel = "configs/experiment/" + row["experiment"] + ".json"
        ep = json.loads((root / rel).read_bytes())
        ep["cells"][0]["readiness"] = {"state": "ready", "requirements": [{"kind": "decision", "sha256": "f" * 64}]}
        write(root, rel, ep)
    assert len(checked(root, population, pin, extent, mapping)) == 4


@pytest.mark.parametrize("mapped", [False, True])
def test_real_legacy_and_mapped_root_decision_keep_exact_pair_checks(tmp_path, mapped):
    root, population, pop_pin, extent, mapping = fixture(tmp_path)
    data = tmp_path / "data"
    data.mkdir()
    source = "b" * 40
    prep_pin = write(root, "docs/readiness/preparation.json", {"prepared_source_commit": source})
    map_pin = write(root, "docs/readiness/identity-map.json", mapping) if mapped else None
    cells = checked(root, population, pop_pin, extent, mapping) if mapped else []
    if not mapped:
        for m in population["architecture"]["members"]:
            stem = "slurp-native-stage3-simple-consumption-" + m["member_id"] + "-n100-v1"
            # Decision 243 (2026-10-10) retired three of these unflown cells (readiness superseded), which
            # campaign loading refuses by design; this test proves the pair checks against their registered
            # bytes, so the fixture's COPY of the fragment is marked ready (the real repository is untouched).
            fragment = root / "configs/experiment" / (stem + ".json")
            doc = json.loads(fragment.read_text(encoding="utf-8"))
            for cell_doc in doc["cells"]:
                cell_doc["readiness"]["state"] = "ready"
            fragment.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
            c, = admission.load_campaign_cells(root, stem)
            v = c.document
            config = admission.compose(root, v["model_fragment"], v["dataset_fragment"], v["baseline_fragment"], stem)
            cells.append((m["member_id"], c, config))
    ids = [run for _, c, v in cells for run in (c.document["run_id"], v.values["native_contact_fit"]["run_id"])]
    decision = dict(schema="saea-campaign-decision-v1", status="decided", owner_decisions=[227],
                    learner_export=False, experiment_population=pop_pin, capacity_prerequisite={},
                    natural_prerequisite={}, source_preparation_commit=source, architecture_extent=extent,
                    eligible_run_ids=ids)
    if mapped: decision["execution_identity_map"] = map_pin
    decision_pin = write(data, "decision.json", decision)
    label, cell, v = cells[0]
    plans = {}
    for role in ("generation", "fit"):
        identity = cell.document if role == "generation" else v.values["native_contact_fit"]
        plans[role] = dict(decision_receipt=decision_pin, preparation_receipt=prep_pin,
                           experiment_population=pop_pin, capacity_prerequisite={}, natural_prerequisite={},
                           architecture_extent=extent, architecture_member=label, cell=cell.document["cell_id"],
                           experiment=cell.document["cell_id"], composed_config_hash=v.config_hash,
                           execution_plan={k: identity[k] for k in ("run_id", "attempt_id")})
        if mapped: plans[role]["execution_identity_map"] = map_pin
    admission._require_n20_root_decision(plans, population, {}, repo_root=root, data_root=data, extent=extent)
    plans["fit"]["composed_config_hash"] = "a" * 64
    with pytest.raises(PolicyError, match="independently composed"):
        admission._require_n20_root_decision(plans, population, {}, repo_root=root, data_root=data, extent=extent)
    plans["fit"]["composed_config_hash"] = v.config_hash
    plans["fit"]["execution_identity_map"] = {"relpath": "foreign.json", "sha256": "f" * 64}
    with pytest.raises(PolicyError, match="identity maps differ"):
        admission._require_n20_root_decision(plans, population, {}, repo_root=root, data_root=data, extent=extent)
    if mapped: plans["fit"]["execution_identity_map"] = map_pin
    else: plans["fit"].pop("execution_identity_map")
    decision["eligible_run_ids"] = list(reversed(ids))
    new_pin = write(data, "decision-reversed.json", decision)
    for plan in plans.values(): plan["decision_receipt"] = new_pin
    with pytest.raises(PolicyError, match="family eligibility"):
        admission._require_n20_root_decision(plans, population, {}, repo_root=root, data_root=data, extent=extent)
