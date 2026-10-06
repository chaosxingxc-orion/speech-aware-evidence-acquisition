"""Prospective history/process continuation of the shared partitioned optimizer.

Retain active parents, all rejected observations and cumulative exposure. Preparation
is offline only; existing reservation, compilation and trial gates remain mandatory.
"""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace
from ..analysis.abstract_population_sources import _external
from ..analysis.abstract_process_feedback import project_process_feedback, compact_process_feedback
from .experiment_population import load_population_config, population_accounting
from .hashing import content_hash
from .system_text_policy import _read_pin, require

SCHEMA = "saea-partitioned-context-optimizer-input-v2"


def continuation_profile(reg):
    """Select a prospectively pinned actor format; historical registrations stay exact."""
    base = {"schema", "status", "parent_input_sha256", "iteration", "population_update_plan",
        "history_completion", "process_completion", "process_registration", "max_actor_input_bytes", "runtime_admission"}
    newer = reg.get("schema") == "saea-partitioned-context-continuation-registration-v2"
    require(set(reg) == base | ({"learner_profile"} if newer else set())
            and (newer and reg["learner_profile"] == "aggregate-template-records-v1"
                 or not newer and reg.get("schema") == "saea-partitioned-context-continuation-registration-v1")
            and reg["status"] == "ROOT_REGISTERED" and reg["runtime_admission"] is False
            and type(reg["max_actor_input_bytes"]) is int and reg["max_actor_input_bytes"] > 0,
            "exact prospective continuation registration required")
    return reg.get("learner_profile")


def _identity(packet):
    packet.pop("input_sha256", None)
    packet["input_sha256"] = content_hash(packet)
    return packet


def _history(archive, parent, history, root):
    from .system_context_partitioned_learning import validate_partitioned_packet
    require(history.get("schema") == "saea-rejected-context-learning-history-v1"
            and history.get("runtime_admission") is False and history.get("learner_exported") is False
            and history["active_parent_bundle_ids"] == {k:v["bundle_id"] for k,v in parent["policies"].items()}
            and history["private_custody"]["parent_input_sha256"] == parent["input_sha256"],
            "rejected history must retain exact active parents")
    h = history["learner_history"]
    require(set(h) == {"disposition", "criterion", "utility_before", "utility_after", "observation", "instructions"}
            and h["disposition"] == "rejected-retain-before-population"
            and h["criterion"] == "strict-population-utility-sum"
            and all(type(h[k]) in (int,float) and math.isfinite(h[k]) for k in ("utility_before","utility_after"))
            and h["utility_after"] <= h["utility_before"], "rejected historical disposition required")
    observed = deepcopy(parent)
    observed["learner_view"] = h["observation"]
    policies = {}
    for templates in h["observation"]["templates"].values():
        for cid, t in templates.items():
            bundle = archive.load_policy(t["bundle_id"])
            policies[cid] = {"bundle_id": bundle.bundle_id, "policy": bundle.as_json()}
    observed["policies"] = policies
    # Validate historical templates and numeric episodes through the same v1 gate.
    observed["schema"] = "saea-partitioned-context-optimizer-input-v1"
    for k in ("continuation_evidence", "parent_input_sha256"): observed.pop(k, None)
    join = json.loads(_read_pin(history["private_custody"]["source_projection"]["source_join"], root))
    historical_config = load_population_config(join["projection_config"], repo_root=root)
    active_config = load_population_config(parent["source_population"], repo_root=archive.root)
    require(all(historical_config[k] == active_config[k] for k in
                ("cohorts", "nodes", "sampling", "execution", "proposer", "contact_limits")),
            "historical and active comparison scope differs")
    observed["source_population"] = join["projection_config"]
    observed["budget"] = population_accounting(historical_config)
    validate_partitioned_packet(SimpleNamespace(root=root, load_policy=archive.load_policy), _identity(observed))
    return {k:deepcopy(h[k]) for k in ("disposition", "criterion", "utility_before", "utility_after", "observation")}


def validate_continuation_packet(archive, packet):
    from .system_context_learning import _population_update_input
    from .system_context_partitioned_learning import validate_partitioned_packet
    require(packet.get("schema") == SCHEMA and
            content_hash({k:v for k,v in packet.items() if k != "input_sha256"}) == packet["input_sha256"],
            "immutable continuation packet required")
    evidence = json.loads(_read_pin(packet["continuation_evidence"], archive.root))
    registration = json.loads(_read_pin(packet["registration"], archive.root))
    continuation_profile(registration)
    parent, _, ids = _population_update_input(archive, packet["parent_input_sha256"])
    require(registration["parent_input_sha256"] == parent["input_sha256"]
            and registration["iteration"] == packet["iteration"] == parent["iteration"]+1
            and registration["population_update_plan"] == packet["population_update_plan"]
            and registration["runtime_admission"] is False and registration["status"] == "ROOT_REGISTERED"
            and evidence["parent_input_sha256"] == parent["input_sha256"], "continuation registration differs")
    for k in ("policies", "learner_view", "source_population", "budget", "algorithm", "experience"):
        require(packet[k] == parent[k], "continuation must preserve active parents and original evidence")
    require(packet["feedback_sample_ids"] == evidence["feedback_sample_ids"]
            and set(parent["feedback_sample_ids"]) <= set(packet["feedback_sample_ids"])
            and packet["source_commitment"] == content_hash(evidence), "continuation evidence or exposure differs")
    base = deepcopy(packet)
    base["schema"] = "saea-partitioned-context-optimizer-input-v1"
    for k in ("continuation_evidence", "parent_input_sha256"): del base[k]
    validate_partitioned_packet(archive, _identity(base))
    return packet, packet["population_update_plan"], ids


def continuation_actor_additions(archive, packet):
    evidence = json.loads(_read_pin(packet["continuation_evidence"], archive.root))
    result = {"rejected_history": deepcopy(evidence["rejected_history"]),
              "process_feedback": deepcopy(evidence["process_feedback"])}
    prior = _prior_continuations(archive, packet)
    if prior:
        result["prior_continuations"] = prior
    return result


def _prior_continuations(archive, packet):
    """Keep chronological abstract evidence without exporting private ancestry."""
    from .system_context_learning import _population_update_input
    parent, _, _ = _population_update_input(archive, packet["parent_input_sha256"])
    if parent["schema"] != SCHEMA:
        return []
    additions = continuation_actor_additions(archive, parent)
    prior = additions.pop("prior_continuations", [])
    return prior + [{"iteration": parent["iteration"], **additions}]


def context_packet_lineage(archive, packet):
    """Return every validated input back to the unchanged evaluated population."""
    from .system_context_learning import _population_update_input
    lineage = [packet]
    while packet["schema"] == SCHEMA:
        packet, _, _ = _population_update_input(archive, packet["parent_input_sha256"])
        lineage.append(packet)
    require(packet["schema"] == "saea-partitioned-context-optimizer-input-v1",
            "original active-parent projection required")
    return lineage


def _copy_pin(pin, source_root, archive):
    raw = _read_pin(pin, source_root)
    target = archive.root / pin["relpath"]
    require(target.resolve().is_relative_to(archive.root.resolve()), "archive path escaped")
    if target.exists(): require(target.read_bytes() == raw, "immutable archive pin differs")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream: stream.write(raw)


def prepare_context_continuation(archive, *, registration_pin, repo_root, data_root):
    """Bind root-reviewed immutable artifacts before preparing a new actor packet.

    Completion pins attest prior full source qualification. Recheck their file
    hashes and reconstruct all abstract statistics; do not repeat official scoring.
    All raw files remain private, outside the actor projection.
    """
    from .system_context_learning import _population_update_input
    from .system_context_partitioned_learning import _plan, _partitioned_actor_view
    root, data = Path(repo_root).resolve(), Path(data_root).resolve()
    reg = json.loads(_read_pin(registration_pin, root))
    profile = continuation_profile(reg)
    parent, _, ids = _population_update_input(archive, reg["parent_input_sha256"])
    require(parent["schema"] in ("saea-partitioned-context-optimizer-input-v1", SCHEMA)
            and type(reg["iteration"]) is int and reg["iteration"] == parent["iteration"]+1,
            "continuation requires a validated partitioned parent and its next iteration")
    config = load_population_config(parent["source_population"], repo_root=archive.root)
    _plan(reg["population_update_plan"], config)
    destination = f"context-learning/inputs/partitioned-{reg['population_update_plan']['batch_id']}.json"
    require(not (archive.root / destination).exists(), "continuation input already prepared")
    hr = json.loads(_read_pin(reg["history_completion"], root))
    pr = json.loads(_read_pin(reg["process_completion"], root))
    require(hr.get("schema") == "saea-rejected-history-preparation-complete-v1" and hr.get("status") == "COMPLETE"
            and pr.get("schema") == "saea-complete-process-backfill-reviewed-v1" and pr.get("status") == "COMPLETE_ROOT_REVIEWED"
            and all(r.get("runtime_admission") is False and r.get("learner_exported") is False for r in (hr,pr)),
            "complete root-reviewed history and process receipts required")
    history = _external(hr["output"], data)
    rejected = _history(archive, parent, history, root)
    feedback_ids = sorted(set(parent["feedback_sample_ids"]) | set(history["private_custody"]["feedback_sample_ids"]))
    source_pins = {"history":hr["output"], "process":pr["result"]}
    history_source_join = history["private_custody"]["source_projection"]["source_join"]
    del history
    report = _external(pr["result"], data)
    preg = json.loads(_read_pin(reg["process_registration"], root))
    require(report.get("schema") == "saea-complete-slurp-process-backfill-v1"
            and report["registration_sha256"] == reg["process_registration"]["sha256"]
            and report.get("runtime_admission") is False and report.get("learner_exported") is False
            and report.get("contacts_added") == {"model":0,"official_scorer":0}
            and preg["source_registration"] == history_source_join
            and preg.get("schema") == "saea-slurp-process-backfill-v1" and preg.get("status") == "ROOT_REGISTERED",
            "exact registered complete process source required")
    bindings = {c["cohort_id"]:{m["member_id"]:m for m in c["members"]} for c in preg["cohorts"]}
    process = compact_process_feedback(project_process_feedback(report, config=config, bindings=bindings))
    evidence = {"schema":"saea-context-continuation-evidence-v1", "parent_input_sha256":parent["input_sha256"],
        "feedback_sample_ids":feedback_ids,"source_pins":source_pins,
        "rejected_history":rejected,"process_feedback":process}
    # Source rechecks use streamed digests to avoid reloading large private history.
    for pin in source_pins.values():
        with Path(pin["path"]).open("rb") as stream:
            require(hashlib.file_digest(stream,"sha256").hexdigest() == pin["sha256"], "source changed during preparation")
    for k in ("history_completion","process_completion","process_registration"):
        _read_pin(reg[k], root)
    require(json.loads(_read_pin(registration_pin, root)) == reg, "continuation authority changed")
    packet = deepcopy(parent)
    packet.update(schema=SCHEMA, iteration=reg["iteration"],registration=registration_pin,
        population_update_plan=reg["population_update_plan"], parent_input_sha256=parent["input_sha256"],
        source_commitment=content_hash(evidence),feedback_sample_ids=feedback_ids)
    # Bound the full semantic payload before any archive input or proposal is created.
    preview = {"parents":parent["learner_view"],"history":rejected,"process":process}
    prior = _prior_continuations(archive, packet)
    if prior:
        preview["prior_continuations"] = prior
    if profile is None:
        require(len(json.dumps(preview,ensure_ascii=True).encode()) <= reg["max_actor_input_bytes"], "actor byte budget exceeded")
    _copy_pin(registration_pin, root, archive)
    name = f"context-learning/evidence/{reg['population_update_plan']['batch_id']}.json"
    archive._write(name, evidence)
    packet["continuation_evidence"]={"relpath":name,"sha256":hashlib.sha256((archive.root/name).read_bytes()).hexdigest()}
    _identity(packet)
    validate_continuation_packet(archive, packet)
    actor = _partitioned_actor_view(archive, packet, packet["population_update_plan"], ids)
    require(len(json.dumps(actor,ensure_ascii=True).encode()) <= reg["max_actor_input_bytes"], "actor byte budget exceeded")
    archive._write(destination, packet)
    return packet
