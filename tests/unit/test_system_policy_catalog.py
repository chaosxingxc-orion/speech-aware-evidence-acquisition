"""Source-pinned complete policy configurations; no model/service contacts."""
import copy
import json
import subprocess
from dataclasses import asdict
from pathlib import Path
import pytest
from test_native_episode_runner import _config, _program
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_system_episode_policy import _policy
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.native_episode_config import NativeEpisodeRunBinding
from speech_aware_evidence_acquisition.rails.system_policy_catalog import load_system_policy_catalog
from test_finite_policy_artifacts import write_pin
from test_native_episode_source import source  # noqa: F401
from speech_aware_evidence_acquisition.rails.phase_tools import TASK_CONTRACT_TOOL


@pytest.fixture
def catalog_case(tmp_path):
    repo, data = tmp_path/"repo", tmp_path/"data"
    repo.mkdir(); data.mkdir(); (repo/"configs/probes").mkdir(parents=True)
    raw = {
        "schema":"saea-native-episode-config-v1","episode_id":"native-role-runner-proof-v1",
        "max_revisions":1,"actions":{"accept":"ACCEPT","revise":"REVISE","acquire":"ACQUIRE"},
        "roles":{k:{"phase_id":k,"max_iterations":1} for k in ("perception","solver","reviewer","planner")},
        "exhaustion_policy":"deliver-latest-solver",
    }
    noop = lambda *args: None
    base = NativeEpisodeRunBinding(config=_config(max_revisions=1,max_contacts=7),
        program=_program(max_contacts=7),material_for_phase=noop,render_request=noop,request_gate=noop)
    cold = _policy({"repair":base,"accept":base},("s1","s2"))
    snapshot = write_pin(data,"snapshot.json",cold.snapshot.as_json())
    schedule = write_pin(data,"schedule.json",cold.schedule.as_json())
    assets = []
    for action in ("repair","accept"):
        value = copy.deepcopy(raw)
        if action == "accept": value["max_revisions"] = 0
        assets.append({"action_id":action,"source":write_pin(repo,f"configs/probes/{action}.json",
            {"schema":"saea-system-policy-action-v1","native_episode":value,"phase_tools":{}})})
    spec = {"schema":"saea-system-episode-policy-config-v1",
        "algorithm_id":"finite-system-policy-bandit-v1",
        "snapshot":snapshot,"schedule":schedule,"actions":assets}
    values={"native_episode":raw,"system_episode_policy":spec,
            "stage3_algorithm":{"id":"finite-system-policy-bandit-v1"}}
    return dict(repo_root=repo,data_root=data,values=values,program=base.program,
        expected_roster_ids=("s1","s2"),expected_split_identity_hash="b"*64,
        shared_source_hashes={"model_fragment":content_hash({"frozen":"model"}),
                              "baseline_fragment":content_hash({"shared":"baseline"})})


def test_loads_real_native_configs_within_shared_upper_budget(catalog_case):
    catalog = load_system_policy_catalog(**catalog_case)
    assert catalog.configs["repair"].max_contacts == 7
    assert catalog.configs["accept"].max_contacts == 4
    assert catalog.configs["accept"].max_revisions == 0
    for sid in ("s1","s2"):
        record = catalog.expected_record(sid,query_sha256="d"*64,speech_packet_sha256="e"*64)
        values = catalog.values_for_record(record)
        assert values["native_episode"]["max_revisions"] == (
            1 if record["decision"]["action"] == "repair" else 0)


@pytest.mark.parametrize("mutation", [
    "wrong-bytes","new-top-field","missing-action","outside-root","over-budget",
    "different-index","new-tool-authority","different-label","wrong-roster",
])
def test_bad_action_or_source_cannot_enter_catalog(catalog_case, mutation):
    case = catalog_case
    spec = case["values"]["system_episode_policy"]
    path = case["repo_root"]/spec["actions"][0]["source"]["relpath"]
    asset = json.loads(path.read_text())
    if mutation == "wrong-bytes":
        path.write_text(path.read_text()+" ")
    elif mutation == "new-top-field":
        asset["model"] = "different answering model"
    elif mutation == "missing-action":
        spec["actions"].pop()
    elif mutation == "outside-root":
        spec["actions"][0]["source"]["relpath"] = "../outside.json"
    elif mutation == "over-budget":
        asset["native_episode"]["max_revisions"] = 2
    elif mutation == "different-index":
        asset["native_episode"]["knowledge_index"] = {"unexpected":"binding"}
    elif mutation == "new-tool-authority":
        asset["phase_tools"] = {"reviewer":{"allowed_tools":[TASK_CONTRACT_TOOL],"mode":"native-tools"}}
    elif mutation == "different-label":
        case["values"]["stage3_algorithm"]["id"] = "none"
    else:
        case["expected_roster_ids"] = ("s1",)
    if mutation in {"new-top-field","over-budget","different-index","new-tool-authority"}:
        spec["actions"][0]["source"] = write_pin(case["repo_root"],
            spec["actions"][0]["source"]["relpath"],asset)
    with pytest.raises((ValueError, RuntimeError)):
        load_system_policy_catalog(**case)


@pytest.mark.parametrize("with_tools", [False, True])
def test_catalog_dispatches_real_flight_graph_and_seals_each_selected_policy(catalog_case, tmp_path, monkeypatch, with_tools):
    from types import SimpleNamespace
    from test_native_episode_runner import _ActualEpisodeHarness
    from test_rails_runner import _knowledge_snapshot
    from speech_aware_evidence_acquisition.core.flight import runtime as flight_module
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    from speech_aware_evidence_acquisition.core import preparation_fit
    from speech_aware_evidence_acquisition.rails.phase_runner import run_continuous_program
    ceiling = 9 if with_tools else 7
    harness = _ActualEpisodeHarness(
        tmp_path/"graph", sample_count=2, max_revisions=1, max_contacts=ceiling,
        planner_actions=("REVISE","ACCEPT"), arm="speech-feature-query-native-tools" if with_tools else "speech-feature-query",
        reviewer_task_tool=with_tools)
    case = catalog_case
    values = copy.deepcopy(case["values"])
    if with_tools:
        values["native_episode"]["roles"]["reviewer"]["max_iterations"] = 2
        values["phase_tools"] = {
            "reviewer":{"mode":"native-tools","source_authority_role":"reviewer","allowed_tools":[TASK_CONTRACT_TOOL]}}
        entry = values["system_episode_policy"]["actions"][0]
        asset = json.loads((case["repo_root"]/entry["source"]["relpath"]).read_text())
        asset["native_episode"]["roles"]["reviewer"]["max_iterations"] = 2
        asset["phase_tools"] = values["phase_tools"]
        entry["source"] = write_pin(case["repo_root"],entry["source"]["relpath"],asset)
        original_output = harness._output
        def output_with_selected_authority(key):
            rendered = harness.prepared[key]["rendered"]
            if key[1] == "reviewer" and not rendered.get("tools"):
                return f"reviewer-analysis:{key[0]}:visit:{key[2]}"
            return original_output(key)
        harness._output = output_with_selected_authority
    schedule_path = case["data_root"]/values["system_episode_policy"]["schedule"]["relpath"]
    schedule = json.loads(schedule_path.read_text())
    schedule["split_identity_hash"] = harness.plan.split_identity_hash
    values["system_episode_policy"]["schedule"] = write_pin(case["data_root"],"schedule.json",schedule)
    values["native_contact_fit"] = {
        "run_id":"SAEA-CATALOG-FIT","attempt_id":"attempt-catalog-fit","contact_cap":56}
    runtime = object.__new__(FlightRuntime)
    runtime._composed = SimpleNamespace(values=values)
    values.update(policy=harness.program.program_id, arm=harness.client.arm, scorers=[])
    runtime._model = {"frozen":"model"}
    runtime._baseline = {k:v for k,v in values.items()
                         if k not in {"system_episode_policy","native_contact_fit"}}
    runtime._dataset = {}
    _write_source_fragments(case["repo_root"], runtime._model, runtime._baseline,
                            {k:values[k] for k in ("system_episode_policy","native_contact_fit")})
    runtime._repo_root = case["repo_root"]; runtime._data_root = case["data_root"]
    runtime._adapter = harness.adapter; runtime._split_id = "all"; runtime._plan = harness.plan
    runtime._transport = harness.transport; runtime._arm = lambda: harness.client.arm
    runtime._phase_program_material = {
        "knowledge_snapshot":_knowledge_snapshot(),"speech_packet_bindings":harness.speech_bindings,
        "material_for_phase":harness.material_for_phase,"trace_sink":harness.trace}
    runtime._continuous_phase_runner = run_continuous_program
    runtime._phase_planner_specs = lambda _policy: {}
    runtime._phase_decoding_params = lambda: {"temperature":0,"max_tokens":64}
    runtime._fit_base_plan = lambda plan: plan
    runtime._flight_roster_sample_ids = lambda: ("s1","s2")
    runtime._phase_tool_builder = None
    runtime._phase_knowledge_catalog = lambda snapshot: None
    runtime._candidate_experience_memory = None
    runtime._experience_memory = None
    runtime._speech_observations = None
    runtime._live_speech_config = None
    runtime._record_phase_tool_contact = harness.tools_for_phase.tool_contact if with_tools else None
    def capacity_only(request):
        harness.request_gate(request)
        capacity_only.receipts.append({"capacity_verified":False})
    capacity_only.receipts = []
    monkeypatch.setattr(flight_module,"default_phase_program",lambda _policy:harness.program)
    monkeypatch.setattr(preparation_fit,"build_native_contact_fit_gate",lambda *args:capacity_only)
    try:
        rows, contacts, _, dispatch, phases = runtime._dispatch_phase_program(
            harness.client,harness.plan,harness.program.program_id)
        runtime._output_rows = rows
        canonical = runtime._canonical_output_rows(harness.client)
    finally:
        closed = harness.close()
    assert contacts == closed["request_count"] == (12 if with_tools else 11)
    assert len(canonical) == 2
    assert "phase_tools" not in dispatch
    assert {k:v["episodes"] for k,v in dispatch["system_episode_policy"]["actions"].items()} == {
        "repair":1,"accept":1}
    tool_receipt = dispatch["system_episode_policy"]["actions"]["repair"]["phase_tools"]
    assert (tool_receipt["completed"] if tool_receipt else 0) == (1 if with_tools else 0)
    assert len(harness.tool_contacts) == (1 if with_tools else 0)
    by_id = {row["sample_id"]: row for row in canonical}
    schema_requests = [
        key for key, request in harness.prepared.items()
        if request["rendered"].get("tools")
    ]
    assert bool(schema_requests) == with_tools
    assert all(key[1] == "reviewer" and
               by_id[key[0]]["native_episode_receipt"]["system_policy_decision"]["decision"]["action"] == "repair"
               for key in schema_requests)
    assert {r["native_episode_receipt"]["system_policy_decision"]["decision"]["action"]
            for r in canonical} == {"repair","accept"}
    for row in canonical:
        action = row["native_episode_receipt"]["system_policy_decision"]["decision"]["action"]
        assert row["text"].endswith("visit:2" if action=="repair" else "visit:1")
    _assert_selected_source(runtime, harness, canonical, phases, monkeypatch)
    # The already selected lower-bound policy must not be sealed under the
    # parent's more permissive revision ceiling.
    catalog = runtime._resolved_system_policy_catalog
    short = next(r for r in rows if r["native_episode_receipt"]["system_policy_decision"]["decision"]["action"]=="accept")
    receipt = short["native_episode_receipt"]
    record = receipt["system_policy_decision"]
    with pytest.raises(ValueError,match="contact ceiling"):
        catalog.native_for_episode(receipt,sample_id=short["sample_id"],
            query_sha256=record["pre_action_query_sha256"],
            speech_packet_sha256=record["speech_packet_sha256"],contact_count=5)


def test_source_refuses_unregistered_complete_policy_receipt(source):
    from test_native_episode_source import _write
    from speech_aware_evidence_acquisition.analysis import native_episode_source as module
    row = source["phase_document"]["phases"][0]["results"][0]
    row["native_episode_receipt"]["system_policy_decision"] = {"unregistered":True}
    source["args"]["expected_phase_sha256"] = _write(
        source["args"]["phase_artifact_path"],source["phase_document"])
    with pytest.raises(module.NativeEpisodeSourceError,match="no registered catalog"):
        module.verify_native_episode_source(**source["args"])


def _write_source_fragments(repo, model, baseline, experiment):
    from test_native_episode_source import _write
    for kind,value in (("model",model),("dataset",{}),("baseline",baseline),("experiment",experiment)):
        _write(repo/"configs"/kind/f"{kind}.json",value)
    for cmd in (
        ["git","init","-q"],["git","add","."],
        ["git","-c","user.name=Fixture","-c","user.email=fixture@example.invalid",
         "commit","-qm","Pin selected complete policies"],
    ):
        subprocess.run(cmd,cwd=repo,check=True,capture_output=True)


def _assert_selected_source(runtime, harness, outputs, phases, monkeypatch):
    from test_native_episode_source import _write
    from speech_aware_evidence_acquisition.analysis import native_episode_source as module
    from speech_aware_evidence_acquisition.core.bundle.artifacts import VerifiedBundle
    from speech_aware_evidence_acquisition.core.config import compose
    repo, data = runtime._repo_root, runtime._data_root
    names = {k:k for k in ("model","dataset","baseline","experiment")}
    composed = compose(repo,**names)
    plan = harness.plan
    manifest = {
        "status":"COMPLETED",
        "study_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=repo,text=True).strip(),
        "config":{"fragments":names,"config_hash":composed.config_hash},
        "arm":harness.client.arm,"scorers":[],"plan":asdict(plan),
    }
    run = data/"sealed"; manifest_path=run/"manifest.json"; phase_path=run/"phases.json"
    manifest_sha = _write(manifest_path,manifest)
    phase_sha = _write(phase_path,{
        "schema":"saea-flight-phase-summaries-v1",
        "run_id":plan.run_id,"attempt_id":plan.attempt_id,
        "policy":harness.program.program_id,"phases":[s.as_json() for s in runtime._phase_summaries],
    })
    bundle = VerifiedBundle(manifest_path,manifest,None,tuple(outputs),
        {row["record_id"]:row["payload"] for row in map(json.loads,
            next(harness.world.run_dir.glob("*.trace.jsonl")).read_text().splitlines())},
        frozenset(("s1","s2")),"FINALIZED")
    args = dict(manifest_path=manifest_path,expected_manifest_sha256=manifest_sha,
        phase_artifact_path=phase_path,expected_phase_sha256=phase_sha,repo_root=repo)
    with monkeypatch.context() as patch:
        patch.setattr(module,"verify_bundle",lambda _:bundle)
        patch.setattr(module,"default_phase_program",lambda _:harness.program)
        with pytest.raises(module.NativeEpisodeSourceError,match="pinned data root"):
            module.verify_native_episode_source(**args)
        verified = module.verify_native_episode_source(**args,data_root=data)
        assert verified.sample_ids == ("s1","s2")
        assert verified.diagnostics["sample_count"] == 2
        # An edited action with the same name cannot reinterpret the sealed graph.
        asset = repo/"configs/probes/accept.json"
        original = asset.read_bytes()
        asset.write_bytes(original+b" ")
        patch.setattr(module,"require_clean_study_repo",lambda _:manifest["study_commit"])
        try:
            with pytest.raises(ValueError,match="SHA"):
                module.verify_native_episode_source(**args,data_root=data)
        finally:
            asset.write_bytes(original)
