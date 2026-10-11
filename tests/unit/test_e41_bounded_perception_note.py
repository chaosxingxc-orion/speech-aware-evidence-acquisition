"""Item E41: the bounded Perception note on the Earnings21 + ConEC system form.

Owner decision 103 defines E41 ("a bounded Perception note (structured /
length-constrained instruction) with its own dry run before the sub10 re-read
of the Earnings system form") and decision 158 orders it registered as
unfinished Stage-2 engineering base. These proofs compose the two HELD cells
through the re-pin tool's own identity path and the real native-episode loader,
and pin the registration's model-free facts: zero model, tokenizer, encoder,
server, network and scorer contacts, and no utterance, reference or delivered
text anywhere.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from speech_aware_evidence_acquisition.contracts.ledger import _parse_ledger_tables
from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells
from speech_aware_evidence_acquisition.core.flight.repin import (
    assert_current_pins_present,
    compute_cell_identity,
)
from speech_aware_evidence_acquisition.core.stage3_algorithms import (
    validate_stage3_algorithm_label,
)
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)

REPO = Path(__file__).resolve().parents[2]
_CHECKS = REPO / "scripts" / "checks"
if str(_CHECKS) not in sys.path:
    sys.path.insert(0, str(_CHECKS))

import finite_completion_policy_check as gate  # noqa: E402

RD = REPO / "docs/readiness/2026-09-27-e21-native-window-e41-v1"
PREREG = REPO / "docs/readiness/2026-09-27-e21-native-window-e41-v1-preregistration.md"
PIN = "phase_material.perception.instruction_template"
OLD_PROBE = "probes/e21_native_window_system_perception_v1.txt"
NEW_PROBE = "probes/e21_native_window_system_perception_v2.txt"
V31 = {
    "native_episode.finite_completion_scope",
    "native_episode.roles.perception.max_completion_tokens",
    "native_episode.roles.reviewer.max_completion_tokens",
    "phase_material.reviewer.instruction_template",
}

DRY = ("e21-native-window-four-row-e41-dry-run-v1", "e21-native-window-system-four-row-e41-v1",
       "SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E41-V1")
SUB10 = ("e21-native-window-sub10-e41-v1", "e21-native-window-system-sub10-e41-v1",
         "SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-E41-V1")
E39B = ("e21-native-window-four-row-e39b-dry-run-v1", "e21-native-window-system-four-row-e39b-v1")
E35_SUB10 = ("e21-native-window-sub10-direct-vs-system-v1", "e21-native-window-system-sub10-v1")

#: Every composed leaf the dry run may differ by against E39b besides the one pin.
DRY_BOOKKEEPING = {
    "cells[0].attempt_id", "cells[0].attempt_note", "cells[0].baseline_fragment", "cells[0].cell_id",
    "cells[0].readiness.reason", "cells[0].readiness.requirements",
    "cells[0].readiness.requirements[0].expected_decision_id", "cells[0].readiness.requirements[0].kind",
    "cells[0].readiness.requirements[0].reason", "cells[0].readiness.requirements[0].relpath",
    "cells[0].readiness.requirements[0].sha256", "cells[0].readiness.state", "cells[0].run_id",
    "date", "execution_plan_note", "experiment_id", "native_contact_fit.attempt_id", "native_contact_fit.run_id",
    "native_episode.episode_id", "purpose", "readiness.reason", "stage3_algorithm.id", "stage3_algorithm.note",
    "stage3_algorithm.operators_used", "what_this_is",
}


#: Each cell's own decision id (registered c3b02e38). The dry run was flipped to ready at 55bcc54d with exactly this
#: decision as its one requirement (Earnings pins no prepared supply, item E38); the sub10 cell follows once its
#: own decision is minted.
DECISION_IDS = {
    DRY[2]: "e21-native-window-e41-dry-run-admission-v1",
    SUB10[2]: "e21-native-window-e41-sub10-admission-v1",
}
#: The readiness leaves the flip moves; everything else in DRY_BOOKKEEPING must differ from E39b in either state.
_READINESS_LEAVES = {p for p in DRY_BOOKKEEPING if p.startswith("cells[0].readiness.")}


def _assert_held_or_flipped(readiness: dict, run_id: str) -> None:
    assert readiness["state"] in ("held", "ready"), readiness
    if readiness["state"] == "held":
        assert readiness["requirements"] == [], readiness
    else:
        assert [req["kind"] for req in readiness["requirements"]] == ["decision"], readiness
        assert readiness["requirements"][0]["expected_decision_id"] == DECISION_IDS[run_id]


def _walk(node, prefix=""):
    if isinstance(node, dict):
        if not node:
            yield prefix, {}
        for key, value in node.items():
            yield from _walk(value, f"{prefix}.{key}" if prefix else str(key))
    elif isinstance(node, list):
        if not node:
            yield prefix, []
        for index, value in enumerate(node):
            yield from _walk(value, f"{prefix}[{index}]")
    else:
        yield prefix, node


def _composed(experiment: str, cell_id: str):
    cell = next(c for c in load_campaign_cells(REPO, experiment) if c.document["cell_id"] == cell_id)
    ident = compute_cell_identity(REPO, experiment, cell)
    composed = compose(REPO, ident.model_fragment, ident.dataset_fragment, ident.baseline_fragment, experiment)
    return ident, composed


def _diff(old, new) -> dict[str, tuple]:
    a, b = dict(_walk(dict(old.values))), dict(_walk(dict(new.values)))
    return {p: (a.get(p, "<absent>"), b.get(p, "<absent>")) for p in set(a) | set(b)
            if a.get(p, "<absent>") != b.get(p, "<absent>")}


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. The bounded note itself.
# ---------------------------------------------------------------------------


def test_the_bounded_note_states_its_bound_and_is_not_a_transcript_order():
    text = (REPO / "configs" / NEW_PROBE).read_text(encoding="utf-8")
    assert text.isascii() and text.endswith("\n") and text.count("\n") == 1
    assert "|" not in text
    for clause in ("at most 5 lines", "at most 20 words", "at most 4 spoken words", "Never repeat a line",
                   "do not transcribe", "Stop after line 5", '"1. NONE"', "Do not call any tool."):
        assert clause in text, clause
    # The only mention of a tool forbids calling one.
    assert text.lower().count("tool") == 1
    # v1 stays on disk, byte-unchanged, for every sealed cell that pins it.
    assert (REPO / "configs" / OLD_PROBE).read_bytes().startswith(b"Identify the linguistic evidence")


# ---------------------------------------------------------------------------
# 2. The two held cells compose and load on the real program.
# ---------------------------------------------------------------------------


def test_both_cells_compose_at_base_lock_v31_with_the_bounded_note():
    _, e39b = _composed(*E39B)
    parent_config = load_native_episode_config(e39b.values, default_phase_program(e39b.values["policy"]))
    for experiment, cell_id, run_id in (DRY, SUB10):
        ident, composed = _composed(experiment, cell_id)
        assert ident.run_id == run_id
        config = load_native_episode_config(composed.values, default_phase_program(composed.values["policy"]))
        assert config.finite_completion_scope == "answering-node"
        assert config.finite_completion_policy == "deliver-latest-or-abstain"
        assert config.react_exhaustion_policy == "continue-without-answer"
        assert config.role_completion_caps == {"perception": 640, "reviewer": 640}
        assert config.max_contacts == parent_config.max_contacts
        material = composed.values["phase_material"]
        assert material["perception"]["instruction_template"] == NEW_PROBE
        assert material["reviewer"]["instruction_template"] == "probes/e21_native_window_system_reviewer_v2.txt"
        assert composed.values["serving_geometry"] == e39b.values["serving_geometry"]
        document = _json(REPO / "configs/experiment" / f"{experiment}.json")
        assert set(document["cells"][0]["readiness"]) == {"state", "reason", "requirements"}
        _assert_held_or_flipped(document["cells"][0]["readiness"], run_id)
        record, operators = validate_stage3_algorithm_label(document["stage3_algorithm"], cell=cell_id)
        assert record.id == "none" and operators == ()


def test_the_dry_run_differs_from_e39b_by_one_pin_plus_bookkeeping():
    _, e39b = _composed(*E39B)
    _, dry = _composed(*DRY[:2])
    diff = _diff(e39b, dry)
    assert diff[PIN] == (OLD_PROBE, NEW_PROBE)
    # The readiness leaves differ from E39b while the dry run is held and may coincide in shape once it is
    # flipped (55bcc54d); every other bookkeeping leaf must differ, and nothing outside the list may.
    assert set(diff) - {PIN} <= DRY_BOOKKEEPING, sorted(set(diff) - {PIN} - DRY_BOOKKEEPING)
    assert DRY_BOOKKEEPING - _READINESS_LEAVES <= set(diff), sorted(DRY_BOOKKEEPING - _READINESS_LEAVES - set(diff))
    # No budget, roster, geometry, scorer, instruction or episode leaf moved.
    for path in diff:
        assert not path.startswith(("execution_plan.", "cells[0].execution_plan", "prepared_", "serving_",
                                    "scorers", "task_instruction", "knowledge_", "decoding_params")), path


def test_the_sub10_cell_is_the_e35_sub10_system_arm_plus_v31_plus_the_pin():
    _, e35 = _composed(*E35_SUB10)
    _, sub10 = _composed(*SUB10[:2])
    diff = _diff(e35, sub10)
    assert diff[PIN] == (OLD_PROBE, NEW_PROBE)
    assert V31 <= set(diff)
    for key in ("prepared_execution_units", "prepared_window_feature_packets", "knowledge_snapshot_relpath",
                "knowledge_snapshot_sha256", "population", "task_instruction", "scorers"):
        assert sub10.values[key] == e35.values[key], key
    # The same system form as the dry run: the baselines differ only by roster pins and bookkeeping.
    dry_base = _json(REPO / "configs/baseline/e21-native-window-system-four-row-e41-v1.json")
    sub_base = _json(REPO / "configs/baseline/e21-native-window-system-sub10-e41-v1.json")
    moved = {k for k in set(dry_base) | set(sub_base) if dry_base.get(k) != sub_base.get(k)}
    assert moved == {"prepared_execution_units", "prepared_window_feature_packets", "native_contact_fit",
                     "native_episode", "what_this_is", "readiness"}
    assert {k: v for k, v in dry_base["native_episode"].items() if k != "episode_id"} == {
        k: v for k, v in sub_base["native_episode"].items() if k != "episode_id"}
    assert sub_base["native_contact_fit"]["contact_cap"] == 342 * 11 * 4


# ---------------------------------------------------------------------------
# 3. The package: plans pin the current hashes; the shared protocol quotes none.
# ---------------------------------------------------------------------------


def test_the_package_pins_each_cell_and_the_shared_protocol_quotes_no_cell_hash():
    files = sorted(RD.glob("*.json")) + [PREREG, RD / "README.md"]
    protocol = (RD / "protocol-registered-v1.json").read_text(encoding="utf-8")
    for experiment, cell_id, run_id in (DRY, SUB10):
        ident, _ = _composed(experiment, cell_id)
        assert_current_pins_present(files, ident)
        assert ident.config_hash not in protocol and ident.protocol_hash not in protocol
        prefix = "dry-run" if cell_id == DRY[1] else "sub10"
        other = "sub10" if prefix == "dry-run" else "dry-run"
        for kind in ("generation", "fit"):
            plan = _json(RD / f"{prefix}-{kind}-plan-registered-v1.json")
            assert plan["composed_config_hash"] == ident.config_hash
            assert plan["execution_plan"]["protocol_hash"] == ident.protocol_hash
            assert plan["expected_session_id"] == "serving-e21-native-window-flightruntime-np4-max1024-v1"
            # A flip of one cell can never rewrite the other cell's plans.
            for sibling in ("generation", "fit"):
                text = (RD / f"{other}-{sibling}-plan-registered-v1.json").read_text(encoding="utf-8")
                assert ident.config_hash not in text and ident.protocol_hash not in text


def test_stage3_measurement_is_form_proof_for_both_run_ids():
    facts = _json(RD / "registered-facts-v1.json")
    blocks = facts["stage3_measurement"]
    assert set(blocks) == {DRY[2], SUB10[2]}
    for block in blocks.values():
        assert block["measurement_design"] == "form-proof"
        assert block["claims_benefit"] is False and block["expected_effect_pp"] == 0.0
    assert blocks[DRY[2]]["rows"] == 1 and blocks[SUB10[2]]["rows"] == 10
    fenced = re.search(r"```json\n(.*?)\n```", PREREG.read_text(encoding="utf-8"), re.S).group(1)
    assert json.loads(fenced)["stage3_measurement"] == blocks


def test_the_model_free_argument_and_token_cost_hold_on_the_committed_receipts():
    trace = _json(RD / "perception-trace-read-v1.json")
    pooled = trace["pooled"]
    assert pooled["perception_contacts"] == 354 and pooled["truncated"] == 82
    assert pooled["truncated_within_e41_bound"] == 0
    assert sum(pooled["truncated_modes"].values()) == pooled["truncated"]
    assert set(pooled["truncated_modes"]) <= {"LOOP", "ENUMERATION", "TRANSCRIPT", "PROSE"}
    assert all(value == 0 for key, value in trace["contacts"].items())
    tokens = _json(RD / "instruction-token-measurement-v1.json")
    bound = tokens["completion_side_bound"]
    worst = bound["synthetic_compliant_notes"]["digit_dense_worst_case_compliant_note"]["tokens"]
    assert worst < bound["cap"] == 640
    assert tokens["instruction_files"]["new"]["relpath"] == "configs/" + NEW_PROBE
    assert {k: v for k, v in tokens["contacts"].items() if k != "tokenizer_process_vocab_only"} == {
        k: 0 for k in tokens["contacts"] if k != "tokenizer_process_vocab_only"}


def test_the_comparator_binding_covers_the_e35_sub10_roster_by_ids_and_hashes_only():
    binding = _json(RD / "sub10-comparator-binding-v1.json")
    windows = binding["windows"]
    assert len(windows) == 342 == binding["roster"]["windows"]
    assert len({w["execution_unit_id"] for w in windows}) == 342
    assert binding["e35_system_arm"]["abstained_windows"] == 76
    for window in windows:
        for arm in ("direct", "e35_system"):
            assert re.fullmatch(r"[0-9a-f]{64}", window[arm]["delivery_text_sha256"])
    keys = {key for window in windows for arm in ("direct", "e35_system") for key in window[arm]}
    assert not any(key == "text" or key.endswith("_text") for key in keys)


# ---------------------------------------------------------------------------
# 4. The gate and the ledger.
# ---------------------------------------------------------------------------


def test_the_finite_completion_gate_passes_and_sees_both_held_cells():
    data = gate.evaluate(REPO)
    assert data["passed"], data["violations"]
    in_scope = {row["run_id"]: row for row in data["in_scope_plan_cells"]}
    scopes = {row["run_id"]: row for row in data["scope_report"]}
    for run_id in (DRY[2], SUB10[2]):
        if run_id not in in_scope:
            # the dry run flew and sealed (attempt-e21-native-window-system-four-row-e41-v1, 2026-09-28): historical, reported only
            assert run_id == DRY[2], run_id
            continue
        # held as registered; the dry run was ready after its flip (55bcc54d)
        assert in_scope[run_id]["readiness_state"] in ("held", "ready")
    for run_id in (DRY[2], SUB10[2]):
        if run_id not in scopes:
            assert run_id == DRY[2], run_id
            continue
        assert scopes[run_id][gate.SCOPE_KEY] == "answering-node"
        assert scopes[run_id]["role_completion_caps"] == {"perception": 640, "reviewer": 640}


def test_the_ledger_carries_five_unconsumed_draft_rows_with_no_pipe_in_any_cell():
    text = (REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    rows = {row["run/experiment id"]: row for row in _parse_ledger_tables(text)}
    expected = [DRY[2], DRY[2] + "-FIT-V1", SUB10[2], SUB10[2] + "-FIT-V1", "SAEA-E21-E41-PERCEPTION-NOTE-TRACE-READ-V1"]
    for run_id in expected:
        row = rows[run_id]
        # DRAFT as registered; countersigned before contact (c75ad044 for the dry run's two rows); consumed once
        # a flight seals.
        assert row["consumed"] in ("no", "yes")
        assert row["consumed"] == "yes" or (
            "DRAFT, root countersignature pending" in row["notes"] or "root countersigned" in row["notes"]
        ), row["notes"][:200]
    raw = [line for line in text.splitlines() if any(f"| {r} |" in line for r in expected)]
    assert len(raw) == 5 and all(line.count("|") == 16 for line in raw)
