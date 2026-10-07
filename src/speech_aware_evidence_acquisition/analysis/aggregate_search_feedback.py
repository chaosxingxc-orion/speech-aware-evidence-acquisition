"""Prepare qualified aggregate evidence independently of the next search size.

Keep every original observation and its private exposure. This adapter neither
selects new parents nor reserves proposals, exports actor inputs or admits runtime.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .abstract_population_sources import _external, read_registered_population_sources
from .aggregate_template_learning import PROFILE, _round
from ..rails.hashing import content_hash
from ..rails.system_context_continuation import _history
from ..rails.system_context_learning import _population_update_input
from ..rails.system_context_partitioned_learning import _partitioned_actor_view
from ..rails.system_context_partitioned_trial import _source_identity
from ..rails.system_text_policy import _read_pin, require


def _verify_private_pin(pin, root, data):
    require(isinstance(pin, dict) and set(pin) in (
                {"path", "sha256"}, {"path", "sha256", "cell_id"}),
            "exact private source pin required")
    # The complete process producer annotates per-member score pins. The label
    # is private metadata, never a substitute for path confinement or byte identity.
    if "cell_id" in pin:
        require(isinstance(pin["cell_id"], str) and bool(pin["cell_id"].strip()),
                "private source cell annotation must be nonempty text")
    path = Path(pin["path"]).resolve()
    require(path.is_relative_to(root) or path.is_relative_to(data),
            "private source escaped registered roots")
    with path.open("rb") as stream:
        require(hashlib.file_digest(stream, "sha256").hexdigest() == pin["sha256"],
                "private source changed during preparation")


def prepare_aggregate_search_feedback(archive, *, registration_pin, repo_root, data_root):
    """Bind complete root-reviewed evidence to an immutable aggregate-only view.

    Requalify current sources before reading results and again before writing.
    Retain historical population sizes; the next search configuration is separate.
    """
    root, data = Path(repo_root).resolve(), Path(data_root).resolve()
    reg = json.loads(_read_pin(registration_pin, root))
    require(set(reg) == {"schema", "status", "parent_input_sha256", "source_registration",
                        "history_completion", "process_completion", "max_feedback_bytes"}
            and reg["schema"] == "saea-aggregate-search-feedback-registration-v1"
            and reg["status"] == "ROOT_REGISTERED"
            and type(reg["max_feedback_bytes"]) is int and reg["max_feedback_bytes"] > 0,
            "exact aggregate evidence registration required")
    destination = f"context-learning/search-feedback/{content_hash(registration_pin)}.json"
    require(not (archive.root / destination).exists(), "aggregate feedback already prepared")
    read_args = dict(source_registration_pin=reg["source_registration"], repo_root=root, data_root=data)
    joined = read_registered_population_sources(**read_args)
    hr = json.loads(_read_pin(reg["history_completion"], root))
    pr = json.loads(_read_pin(reg["process_completion"], root))
    require(hr.get("schema") == "saea-rejected-history-preparation-complete-v1"
            and hr.get("status") == "COMPLETE"
            and pr.get("schema") == "saea-complete-trial-process-preparation-receipt-v1"
            and pr.get("status") == "COMPLETE_ROOT_PROCESS_FEEDBACK_PREPARED"
            and all(r.get("runtime_admission") is False and r.get("learner_exported") is False for r in (hr, pr)),
            "complete root-reviewed evidence receipts required")
    history = _external(hr["output"], data)
    process = json.loads(_read_pin(pr["process_feedback"], data))
    require(process.get("schema") == "saea-complete-root-process-feedback-v1"
            and process.get("runtime_admission") is False and process.get("learner_exported") is False
            and process.get("contacts_added") == {"model": 0, "official_scorer": 0}
            and process["source_registration"] == reg["source_registration"]
                == history["private_custody"]["source_projection"]["source_join"],
            "history and process must bind the same qualified complete source")
    pins = [hr["output"], process["plan"], *process["private_source_pins"]]
    require(bool(process["private_source_pins"]), "source-bound process evidence required")
    for pin in pins:
        _verify_private_pin(pin, root, data)
    parent, plan, ids = _population_update_input(archive, reg["parent_input_sha256"])
    base = _partitioned_actor_view(archive, parent, plan, ids)
    require(base.get("schema") == "saea-aggregate-template-actor-view-v1"
            and base.get("learner_profile") == PROFILE, "validated aggregate parent history required")
    rejected = _history(archive, parent, history, root)
    compact = process["process_feedback"]
    require(base["process_encoding"] in (None, compact["encoding"]), "process encoding differs from history")
    feedback = {k: deepcopy(base[k]) for k in ("records", "comparators", "statistic_columns", "limitations")}
    feedback.update(schema="saea-aggregate-search-feedback-view-v1", process_encoding=deepcopy(compact["encoding"]))
    previous_count = len(feedback["records"])
    _round(rejected["observation"], iteration=parent["iteration"], disposition=rejected["disposition"],
           process=compact, ids=ids, active={cid: parent["policies"][cid]["bundle_id"] for cid in ids},
           records=feedback["records"], comparators=feedback["comparators"],
           selection={k: rejected[k] for k in ("criterion", "utility_before", "utility_after")})
    require(len(feedback["records"]) == previous_count + len(ids), "every historical proposal must remain")
    counts = Counter(r["evaluated_iteration"] for r in feedback["records"])
    require(list(counts) == sorted(counts) and counts[parent["iteration"]] == len(ids),
            "ordered distinct observed populations required")
    feedback["observed_populations"] = [{"iteration": i, "candidate_records": n} for i, n in counts.items()]
    for record in feedback["records"]:
        record["record_id"] = content_hash(record)
    require(len({r["record_id"] for r in feedback["records"]}) == len(feedback["records"]),
            "distinct historical record identities required")
    feedback["limitations"].update(
        history_count="Sum of original observed population sizes; independent of next search K.",
        active_parent_meaning="Historical original retention only; prospective search parents are separately registered.",
        search_or_adoption_authority=False)
    require(len(json.dumps(feedback, ensure_ascii=True).encode()) <= reg["max_feedback_bytes"],
            "aggregate feedback byte budget exceeded")
    exposure = sorted(set(parent["feedback_sample_ids"]) | set(history["private_custody"]["feedback_sample_ids"]))
    require(_source_identity(read_registered_population_sources(**read_args)) == _source_identity(joined),
            "source evidence or READ authority changed during assembly")
    for pin in pins:
        _verify_private_pin(pin, root, data)
    for key in ("history_completion", "process_completion", "source_registration"):
        _read_pin(reg[key], root)
    _read_pin(pr["process_feedback"], data)
    _read_pin(registration_pin, root)
    record = {"schema": "saea-qualified-aggregate-search-feedback-v1", "registration": registration_pin,
        "aggregate_feedback": feedback, "private_custody": {"feedback_sample_ids": exposure,
            "parent_input_sha256": parent["input_sha256"], "source_registration": reg["source_registration"],
            "history_completion": reg["history_completion"], "process_completion": reg["process_completion"]},
        "runtime_admission": False, "learner_exported": False, "proposal_allocation_granted": False,
        "contacts_added": {"model": 0, "official_scorer": 0}}
    record["feedback_sha256"] = content_hash(record)
    archive._write(destination, record)
    return record
