"""Validate the prospective wire description against actual shared parser code.

Use historic proposal bytes and synthetic field-only fixtures. Do not compile new
bundles, inspect private parent contents, reserve attempts or contact any service.
"""
import hashlib
import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError, TextPolicyUpdateProposal, TEXT_CHARACTER_CAP, _context_changes,
)
from audit_static import read_pinned


def main():
    described = json.loads((HERE / "wire-contract-v2.json").read_text())
    current = read_pinned("actor-capsule-v1/output-contract.json")
    original = read_pinned("original-response-v1.json")
    wire = described["wire_contract"]
    assert all(wire[key] == current[key] for key in wire)
    assert set(original) == set(wire["response_fields"])
    assert original["schema"] == wire["response_schema"]
    checked = 0
    for branch in original["branches"]:
        assert set(branch) == set(wire["branch_fields"])
        assert set(branch["proposal"]) == set(wire["proposal_fields"])
        assert branch["proposal"]["schema"] == wire["proposal_schema"]
        assert branch["proposal"]["algorithm"] == wire["algorithm"]
        assert branch["proposal"]["component"] == wire["component"]
        assert branch["experience_operations"] == []
        TextPolicyUpdateProposal.from_context_json(branch["proposal"])
        checked += 1
    assembly_checks = 0
    for placement, tools, history in itertools.product(
        wire["editable"]["context_layout"]["native_role_query_placement"],
        wire["editable"]["node_context"]["tool_schema_rendering"],
        wire["editable"]["node_context"]["reviewer_history_scope"],
    ):
        _context_changes({"context_layout":{"native_role_query_placement":placement},
          "node_context":{"tool_schema_rendering":tools,"reviewer_history_scope":history}})
        assembly_checks += 1
    invalid = [
      {"context_layout":{"native_role_query_placement":"after-knowledge-v2"}},
      {"node_context":{"tool_schema_rendering":"per-role"}},
      {"node_context":{"tool_schema_rendering":"hidden","reviewer_history_scope":"full"}},
      {"node_context":{"tool_schema_rendering":"per-role","reviewer_history_scope":"summary"}},
      {"role_text":{"new_answerer":"Forbidden extra role."}},
      {"knowledge":{"rewrite":"Forbidden edit."}},
    ]
    for fixture in invalid:
        try:
            _context_changes(fixture)
        except PolicyError:
            continue
        raise AssertionError("Invalid synthetic surface was accepted")
    source = ROOT / "src/speech_aware_evidence_acquisition/rails/system_text_policy.py"
    print(json.dumps({"schema":"saea-proposer-contract-compatibility-check-v1", "status":"PASS",
      "existing_original_proposals_validated":checked, "legal_assembly_combinations_validated":assembly_checks,
      "invalid_synthetic_edit_surfaces_rejected":len(invalid), "wire_fields_equal_to_existing_contract":True,
      "current_text_character_cap":TEXT_CHARACTER_CAP, "compiler_source":{"path":str(source.relative_to(ROOT)),
      "sha256":hashlib.sha256(source.read_bytes()).hexdigest()},
      "new_proposals_generated":0,"new_policy_bundles_compiled":0,"model_contacts":0,
      "limitation":"Actual shared proposal parser and field validators exercised; future original response, bundle compilation, capacity and runtime compatibility are not yet proven."},indent=2))

if __name__ == "__main__":
    main()
