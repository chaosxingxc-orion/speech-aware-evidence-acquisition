"""One source-bound Solver capacity recovery, using synthetic evidence only."""

from copy import deepcopy
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from test_architecture_capacity_family import example

LABELS = ["seed", "seed-aa", "review-off", "solver-lookup"]
MEMBER_KEYS = (
    "label",
    "member_id",
    "population_cohort",
    "execution_config",
    "execution_identity_sha256",
    "model_per_trajectory",
    "rehearsal_profile",
    "run_id",
    "attempt_id",
    "composed_config_hash",
    "capacity",
    "graph",
    "graph_config_hash",
    "graph_sample_ids",
    "contact_cap",
    "expected_rows",
    "graph_rows",
)
REGISTRATION_KEYS = (
    "schema",
    "experiment_population",
    "sampling",
    "execution",
    "worker",
    "worker_commit",
    "budget",
    "new_receipt_root",
)


def raw_pin(document, name):
    raw = json.dumps(document, sort_keys=True).encode()
    return raw, {"path": "/data/" + name, "sha256": hashlib.sha256(raw).hexdigest()}


def binding(registration):
    return {
        **{k: deepcopy(registration[k]) for k in REGISTRATION_KEYS},
        "members": [
            {k: deepcopy(m[k]) for k in MEMBER_KEYS} for m in registration["members"]
        ],
    }


def seal(case):
    a, original, disposition, compatibility = case
    raw, pin = raw_pin(original, "original-evidence.json")
    a.update(original_evidence_bytes=raw, original_evidence_pin=pin)
    reg = a["recovery"]["registration"]
    reg.update(
        original_evidence=pin,
        original_registration=original["pins"]["registration"],
        original_finished=original["pins"]["finished"],
        original_windows_exit=original["pins"]["windows_exit"],
    )
    compatibility["source_commits"] = {
        "original": original["registration"]["worker_commit"],
        "recovery": reg["worker_commit"],
    }
    raw, pin = raw_pin(compatibility, "source-compatibility.json")
    a.update(source_compatibility_bytes=raw, source_compatibility_pin=pin)
    reg["source_compatibility"] = pin
    disposition.update(
        original_evidence_sha256=content_hash(original),
        original_registration_sha256=content_hash(original["registration"]),
        recovery_binding_sha256=content_hash(binding(reg)),
        source_compatibility=pin,
        failed_contacts=a["failed_contacts_pin"],
    )
    raw, pin = raw_pin(disposition, "root-recovery-disposition.json")
    a.update(root_disposition_bytes=raw, root_disposition_pin=pin)
    reg["root_recovery_disposition"] = pin
    a["recovery"]["original_registration"] = deepcopy(reg)
    return a


def fixture():
    base = example()
    for m in base["registration"]["members"]:
        m.update(
            capacity="capacity-" + m["label"],
            graph="graph-" + m["label"],
            graph_config_hash=base["graph_config_hashes"][m["label"]],
        )
    reg = base["registration"]
    reg["new_receipt_root"] = "/data/original"
    original = {
        k: deepcopy(base[k])
        for k in (
            "registration",
            "source_check",
            "finished",
            "windows_exit",
            "member_terminals",
            "receipts",
        )
    }
    original["original_registration"] = deepcopy(reg)
    original["finished"].update(exit_code=1, failure="Member solver-lookup failed")
    original["windows_exit"]["exit_code"] = 1
    original["finished"]["members"][-1]["exit_code"] = 1
    original["member_terminals"]["solver-lookup"]["exit_code"] = 1
    original["member_terminals"]["solver-lookup"]["members"][0].update(
        exit_code=1, lease_exit_code=2
    )
    del original["receipts"]["solver-lookup"]
    original["pins"] = {
        key: raw_pin(original[key], "original-" + key + ".json")[1]
        for key in ("registration", "finished", "windows_exit")
    }
    recovery_reg = deepcopy(reg)
    recovery_reg.update(
        schema="saea-architecture-capacity-recovery-entry-v1",
        worker="new-frozen-worker",
        worker_commit="b" * 40,
        new_receipt_root="/data/recovery1",
    )
    member = deepcopy(reg["members"][-1])
    member.update(
        run_id="recovery-run-solver",
        attempt_id="recovery-attempt-solver",
        capacity="recovery-capacity-solver",
        composed_config_hash=content_hash({"fit": "recovery"}),
    )
    recovery_reg["members"] = [member]
    recovery_reg["budget"] = {
        "generation_contacts": 0,
        "scorer_contacts": 0,
        "tokenizer_endpoint_caps": {"solver-lookup": member["contact_cap"]},
        "tokenizer_endpoints_total": member["contact_cap"],
    }
    recovery = {
        "registration": recovery_reg,
        "source_check": deepcopy(base["source_check"]),
        "finished": deepcopy(base["finished"]),
        "windows_exit": {"exit_code": 0},
        "member_terminals": {
            "solver-lookup": deepcopy(base["member_terminals"]["solver-lookup"])
        },
        "receipts": {"solver-lookup": deepcopy(base["receipts"]["solver-lookup"])},
    }
    recovery["source_check"]["source_commit"] = recovery_reg["worker_commit"]
    recovery_reg["source_check_sha256"] = content_hash(recovery["source_check"])
    recovery["finished"]["members"] = [deepcopy(base["finished"]["members"][-1])]
    for terminal in (
        recovery["finished"]["members"][0],
        recovery["member_terminals"]["solver-lookup"]["members"][0],
    ):
        terminal.update(run_id=member["run_id"], attempt_id=member["attempt_id"])
    recovery["receipts"]["solver-lookup"]["inputs"].update(
        source_commit=recovery_reg["worker_commit"],
        config_hash=member["composed_config_hash"],
    )
    contacts = [
        dict(
            run_id=reg["members"][-1]["run_id"],
            attempt_id=reg["members"][-1]["attempt_id"],
            contact=n,
            method="GET" if n == 1 else "POST",
            route="/props" if n == 1 else "/tokenize",
        )
        for n in range(1, 144)
    ]
    contact_bytes = (
        "\n".join(json.dumps(c, sort_keys=True) for c in contacts) + "\n"
    ).encode()
    a = {
        k: deepcopy(base[k])
        for k in (
            "population",
            "population_pin",
            "policy_config_bytes",
            "output_reserve",
            "structural_reserve",
            "slot_tokens",
        )
    }
    a.update(
        recovery=recovery,
        failed_contacts_bytes=contact_bytes,
        failed_contacts_pin={
            "path": "/data/original/solver.contacts.jsonl",
            "sha256": hashlib.sha256(contact_bytes).hexdigest(),
        },
        graph_config_hashes={
            "original": deepcopy(base["graph_config_hashes"]),
            "recovery": {"solver-lookup": base["graph_config_hashes"]["solver-lookup"]},
        },
    )
    compatibility = {
        "schema": "saea-architecture-capacity-source-compatibility-v1",
        "status": "ROOT-VERIFIED",
        "scope": "solver-lookup-routing-only",
        "experiment_population": deepcopy(base["population_pin"]),
        "reused_member_ids": LABELS[:3],
        "changed_member_id": "solver-lookup",
        "passed": True,
        "generation_contacts": 0,
        "tokenizer_contacts": 0,
        "scorer_contacts": 0,
        "unchanged_members": {
            m["label"]: {
                k: deepcopy(m[k])
                for k in (
                    "execution_identity_sha256",
                    "graph_config_hash",
                    "graph_sample_ids",
                    "model_per_trajectory",
                )
            }
            for m in reg["members"][:3]
        },
    }
    disposition = {
        "schema": "saea-architecture-capacity-root-recovery-disposition-v1",
        "status": "decided",
        "scope": "nongenerative-architecture-capacity-recovery-only",
        "recovery_ordinal": 1,
        "experiment_population": deepcopy(base["population_pin"]),
        "reused_member_ids": LABELS[:3],
        "recovered_member_id": "solver-lookup",
    }
    case = a, original, disposition, compatibility
    seal(case)
    return case


def invoke(a):
    from speech_aware_evidence_acquisition.rails.system_context_structural_entry import (
        qualify_architecture_capacity_recovery,
    )

    return qualify_architecture_capacity_recovery(**a)


def test_recovery_reuses_three_original_members_without_rewriting_failed_source():
    a, original, _, _ = fixture()
    before = deepcopy(a)
    result = invoke(a)
    assert a == before
    assert result["schema"] == "saea-architecture-capacity-recovery-review-v1"
    assert [m["label"] for m in result["members"]] == LABELS
    assert [m["source"] for m in result["members"]] == ["original"] * 3 + ["recovery"]
    assert [s["exit_code"] for s in result["sources"]] == [1, 0]
    assert result["failed_attempt_tokenizer_endpoints"] == 143
    assert (
        result["tokenizer_endpoints"] == 480
        and result["spent_tokenizer_endpoints"] == 623
    )
    assert result["generation_contacts"] == result["scorer_contacts"] == 0
    assert result["runtime_admission"] is False and result["read_authorized"] is False
    assert result["root_review_required"] is True
    assert result["original_evidence_sha256"] == content_hash(original)


@pytest.mark.parametrize(
    "fault",
    [
        "original_success",
        "wrong_failed_member",
        "failed_reuse",
        "missing_original_member",
        "duplicate_original_member",
        "extra_success_receipt",
        "missing_success_receipt",
        "cross_source_receipt",
        "bad_original_lease",
        "bad_original_observer",
        "recovery_failed",
        "recovery_failed_lease",
        "recovery_partial",
        "recovery_extra_member",
        "recovery_old_run",
        "recovery_old_attempt",
        "recovery_same_worker",
        "recovery_wrong_schema",
        "changed_policy",
        "changed_graph",
        "changed_roster",
        "changed_geometry",
        "generation",
        "scoring",
        "wrong_budget",
        "unsigned",
        "second_recovery",
        "wrong_scope",
        "wrong_reuse",
        "wrong_target",
        "compatibility_failed",
        "compatibility_wrong_member",
        "compatibility_changed_graph",
        "compatibility_contacts",
        "wrong_source_check",
        "wrong_graph_evidence",
        "original_registration_drift",
        "missing_original",
        "malformed_recovery",
    ],
)
def test_reject_crossbound_partial_or_unapproved_recovery(fault):
    case = fixture()
    a, old, decision, compatible = case
    new = a["recovery"]
    member = new["registration"]["members"][0]
    if fault == "original_success":
        old["finished"].update(exit_code=0, failure=None)
        old["windows_exit"]["exit_code"] = 0
    elif fault == "wrong_failed_member":
        old["finished"]["members"][0]["exit_code"] = 1
    elif fault == "failed_reuse":
        old["member_terminals"]["seed"]["exit_code"] = 1
    elif fault == "missing_original_member":
        old["registration"]["members"].pop(0)
        old["original_registration"] = deepcopy(old["registration"])
    elif fault == "duplicate_original_member":
        old["registration"]["members"][1] = deepcopy(old["registration"]["members"][0])
        old["original_registration"] = deepcopy(old["registration"])
    elif fault == "extra_success_receipt":
        old["receipts"]["solver-lookup"] = deepcopy(new["receipts"]["solver-lookup"])
    elif fault == "missing_success_receipt":
        del old["receipts"]["seed-aa"]
    elif fault == "cross_source_receipt":
        new["receipts"]["solver-lookup"]["inputs"]["source_commit"] = "a" * 40
    elif fault == "bad_original_lease":
        old["member_terminals"]["seed"]["members"][0]["lease_exit_code"] = 2
    elif fault == "bad_original_observer":
        old["finished"]["members"][0]["observer_exit_code"] = 1
    elif fault == "recovery_failed":
        new["finished"]["exit_code"] = new["windows_exit"]["exit_code"] = 1
    elif fault == "recovery_failed_lease":
        new["member_terminals"]["solver-lookup"]["members"][0]["lease_exit_code"] = 2
    elif fault == "recovery_partial":
        new["finished"]["members"] = []
    elif fault == "recovery_extra_member":
        new["registration"]["members"].append(
            deepcopy(old["registration"]["members"][0])
        )
    elif fault == "recovery_old_run":
        member["run_id"] = old["registration"]["members"][-1]["run_id"]
    elif fault == "recovery_old_attempt":
        member["attempt_id"] = old["registration"]["members"][-1]["attempt_id"]
    elif fault == "recovery_same_worker":
        new["registration"]["worker_commit"] = old["registration"]["worker_commit"]
    elif fault == "recovery_wrong_schema":
        new["registration"]["schema"] = old["registration"]["schema"]
    elif fault == "changed_policy":
        member["execution_config"]["sha256"] = "c" * 64
    elif fault == "changed_graph":
        member["graph_config_hash"] = "c" * 64
    elif fault == "changed_roster":
        member["graph_sample_ids"].reverse()
    elif fault == "changed_geometry":
        new["registration"]["execution"]["slot_count"] = 1
    elif fault == "generation":
        new["finished"]["generation_contacts"] = 1
    elif fault == "scoring":
        new["receipts"]["solver-lookup"]["output"]["scorer_contacts"] = 1
        r = new["receipts"]["solver-lookup"]
        r["output_sha256"] = content_hash(r["output"])
    elif fault == "wrong_budget":
        new["registration"]["budget"]["tokenizer_endpoints_total"] += 1
    elif fault == "unsigned":
        decision["status"] = "draft"
    elif fault == "second_recovery":
        decision["recovery_ordinal"] = 2
    elif fault == "wrong_scope":
        decision["scope"] = "generation"
    elif fault == "wrong_reuse":
        decision["reused_member_ids"] = LABELS[1:]
    elif fault == "wrong_target":
        decision["recovered_member_id"] = "seed"
    elif fault == "compatibility_failed":
        compatible["passed"] = False
    elif fault == "compatibility_wrong_member":
        compatible["changed_member_id"] = "seed"
    elif fault == "compatibility_changed_graph":
        compatible["unchanged_members"]["seed"]["graph_config_hash"] = "c" * 64
    elif fault == "compatibility_contacts":
        compatible["tokenizer_contacts"] = 1
    elif fault == "wrong_source_check":
        new["source_check"]["source_commit"] = "c" * 40
    elif fault == "wrong_graph_evidence":
        a["graph_config_hashes"]["original"]["seed"] = "c" * 64
    elif fault == "original_registration_drift":
        old["registration"]["worker"] = "other"
    elif fault == "missing_original":
        del old["member_terminals"]["solver-lookup"]
    elif fault == "malformed_recovery":
        new["member_terminals"] = None
    seal(case)
    with pytest.raises(ValueError):
        invoke(a)


@pytest.mark.parametrize(
    "fault",
    [
        "gap",
        "foreign_run",
        "foreign_attempt",
        "generation_route",
        "bool_index",
        "empty",
        "over_cap",
    ],
)
def test_failed_original_spend_requires_its_exact_bounded_endpoint_log(fault):
    case = fixture()
    a = case[0]
    rows = [json.loads(line) for line in a["failed_contacts_bytes"].splitlines()]
    if fault == "gap":
        rows[2]["contact"] = 9
    elif fault == "foreign_run":
        rows[0]["run_id"] = "foreign"
    elif fault == "foreign_attempt":
        rows[0]["attempt_id"] = "foreign"
    elif fault == "generation_route":
        rows[0].update(method="POST", route="/v1/chat/completions")
    elif fault == "bool_index":
        rows[0]["contact"] = True
    elif fault == "empty":
        rows = []
    else:
        rows = [dict(rows[-1], contact=n) for n in range(1, 502)]
    a["failed_contacts_bytes"] = (
        "\n".join(json.dumps(r) for r in rows) + "\n"
    ).encode()
    a["failed_contacts_pin"]["sha256"] = hashlib.sha256(
        a["failed_contacts_bytes"]
    ).hexdigest()
    seal(case)
    with pytest.raises(ValueError):
        invoke(a)


@pytest.mark.parametrize(
    "stem",
    [
        "original_evidence",
        "root_disposition",
        "source_compatibility",
        "failed_contacts",
    ],
)
def test_raw_authority_and_failure_bytes_are_hash_bound(stem):
    a = fixture()[0]
    a[stem + "_bytes"] += b" "
    with pytest.raises(ValueError):
        invoke(a)


def test_recovery_binding_excludes_authority_cycle_but_includes_launch_cell():
    from speech_aware_evidence_acquisition.rails.system_context_structural_entry import (
        architecture_capacity_recovery_binding,
    )

    a = fixture()[0]
    reg = a["recovery"]["registration"]
    before = architecture_capacity_recovery_binding(reg)
    reg["root_recovery_disposition"] = {"path": "different", "sha256": "c" * 64}
    reg["source_check_sha256"] = "d" * 64
    assert architecture_capacity_recovery_binding(reg) == before
    reg["members"][0]["capacity"] = "foreign-cell"
    assert architecture_capacity_recovery_binding(reg) != before


@pytest.mark.parametrize(
    "field",
    [
        "original_registration",
        "original_finished",
        "original_windows_exit",
        "original_evidence",
        "root_recovery_disposition",
        "source_compatibility",
    ],
)
def test_recovery_cannot_rebind_original_or_authority_pins(field):
    a = fixture()[0]
    a["recovery"]["registration"][field] = {
        "path": "/data/foreign.json",
        "sha256": "c" * 64,
    }
    a["recovery"]["original_registration"] = deepcopy(a["recovery"]["registration"])
    with pytest.raises(ValueError):
        invoke(a)


@pytest.mark.parametrize(
    "field",
    [
        "original_evidence_sha256",
        "original_registration_sha256",
        "recovery_binding_sha256",
    ],
)
def test_root_disposition_cannot_bind_other_source_or_recovery_identity(field):
    a = fixture()[0]
    disposition = json.loads(a["root_disposition_bytes"])
    disposition[field] = "c" * 64
    a["root_disposition_bytes"], a["root_disposition_pin"] = raw_pin(
        disposition, "altered-disposition.json"
    )
    a["recovery"]["registration"]["root_recovery_disposition"] = a[
        "root_disposition_pin"
    ]
    a["recovery"]["original_registration"] = deepcopy(a["recovery"]["registration"])
    with pytest.raises(ValueError):
        invoke(a)


@pytest.mark.parametrize(
    "fault",
    [
        "malformed_pin",
        "boolean_ordinal",
        "boolean_generation",
        "unknown_family",
        "graph_sources",
    ],
)
def test_recovery_scope_and_typed_counters_fail_closed(fault):
    case = fixture()
    a, old, decision, _ = case
    if fault == "malformed_pin":
        a["failed_contacts_pin"]["extra"] = 0
    elif fault == "boolean_ordinal":
        decision["recovery_ordinal"] = True
    elif fault == "boolean_generation":
        old["finished"]["generation_contacts"] = False
    elif fault == "unknown_family":
        a["population"]["architecture"]["members"].reverse()
    else:
        a["graph_config_hashes"]["extra"] = {}
    seal(case)
    with pytest.raises(ValueError):
        invoke(a)


def test_recovery_binding_rejects_missing_launch_identity():
    from speech_aware_evidence_acquisition.rails.system_context_structural_entry import (
        architecture_capacity_recovery_binding,
    )

    reg = fixture()[0]["recovery"]["registration"]
    del reg["members"][0]["capacity"]
    with pytest.raises(ValueError):
        architecture_capacity_recovery_binding(reg)


@pytest.mark.parametrize("field", ["runtime_sample_ids", "runtime_graph_sample_ids"])
def test_runtime_order_opt_in_requires_complete_family_api(field):
    case = fixture()
    a, original, _, _ = case
    a["recovery"]["registration"]["members"][0][field] = ["synthetic-order"]
    a["recovery"]["original_registration"] = deepcopy(a["recovery"]["registration"])
    seal(case)
    with pytest.raises(ValueError):
        invoke(a)
